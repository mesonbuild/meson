# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2024 Intel Corporation

"""Interpreter for converting Cargo Toml definitions to Meson AST

There are some notable limits here. We don't even try to convert something with
a build.rs: there's so few limits on what Cargo allows a build.rs (basically
none), and no good way for us to convert them. In that case, an actual meson
port will be required.
"""

from __future__ import annotations
import dataclasses
import functools
import os
import collections
import urllib.parse
import typing as T

from . import builder, version, cfg
from .toml import load_toml
from .manifest import Manifest, CargoLock, Workspace, fixup_meson_varname
from ..mesonlib import MesonException, MachineChoice, version_compare
from .. import coredata, mlog
from ..wrap.wrap import PackageDefinition

if T.TYPE_CHECKING:
    from . import raw
    from .. import mparser
    from .manifest import Dependency, SystemDependency
    from ..environment import Environment
    from ..interpreterbase import SubProject
    from ..compilers.rust import RustCompiler

    from typing_extensions import Literal

def _dependency_name(package_name: str, api: str, suffix: str = '-rs') -> str:
    basename = package_name[:-len(suffix)] if suffix and package_name.endswith(suffix) else package_name
    return f'{basename}-{api}{suffix}'


def _dependency_varname(dep: Dependency) -> str:
    return f'{fixup_meson_varname(dep.package)}_{(dep.api.replace(".", "_"))}_dep'


def _library_name(name: str, api: str, lib_type: Literal['rust', 'c', 'proc-macro'] = 'rust') -> str:
    # Add the API version to the library name to avoid conflicts when multiple
    # versions of the same crate are used. The Ninja backend removed everything
    # after the + to form the crate name.
    if lib_type == 'c':
        return name
    return f'{name}+{api.replace(".", "_")}'


def _extra_args_varname() -> str:
    return 'extra_args'


def _extra_deps_varname() -> str:
    return 'extra_deps'


@dataclasses.dataclass
class PackageState:
    manifest: Manifest
    downloaded: bool = False
    features: T.Set[str] = dataclasses.field(default_factory=set)
    required_deps: T.Set[str] = dataclasses.field(default_factory=set)
    optional_deps_features: T.Dict[str, T.Set[str]] = dataclasses.field(default_factory=lambda: collections.defaultdict(set))
    # If this package is member of a workspace.
    ws_subdir: T.Optional[str] = None
    ws_member: T.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class PackageKey:
    package_name: str
    api: str


@dataclasses.dataclass
class WorkspaceState:
    workspace: Workspace
    subdir: str
    # member path -> PackageState, for all members of this workspace
    packages: T.Dict[str, PackageState] = dataclasses.field(default_factory=dict)
    # package name to member path, for all members of this workspace
    packages_to_member: T.Dict[str, str] = dataclasses.field(default_factory=dict)
    # member paths that are required to be built
    required_members: T.List[str] = dataclasses.field(default_factory=list)


class Interpreter:
    def __init__(self, env: Environment, subdir: str, subprojects_dir: str) -> None:
        self.environment = env
        # Map Cargo.toml's subdir to loaded manifest.
        self.manifests: T.Dict[str, T.Union[Manifest, Workspace]] = {}
        # Map of cargo package (name + api) to its state
        self.packages: T.Dict[PackageKey, PackageState] = {}
        # Map subdir to workspace
        self.workspaces: T.Dict[str, WorkspaceState] = {}
        # Files that should trigger a reconfigure if modified
        self.build_def_files: T.List[str] = []
        # Cargo packages
        filename = os.path.join(self.environment.get_source_dir(), subdir, 'Cargo.lock')
        subprojects_dir = os.path.join(self.environment.get_source_dir(), subprojects_dir)
        self.cargolock = load_cargo_lock(filename, subprojects_dir)
        if self.cargolock:
            self.environment.wrap_resolver.merge_wraps(self.cargolock.wraps)
            self.build_def_files.append(filename)

    def get_build_def_files(self) -> T.List[str]:
        return self.build_def_files

    def interpret(self, subdir: str, project_root: T.Optional[str] = None) -> mparser.CodeBlockNode:
        manifest = self._load_manifest(subdir)
        filename = os.path.join(self.environment.source_dir, subdir, 'Cargo.toml')
        build = builder.Builder(filename)
        if isinstance(manifest, Workspace):
            return self.interpret_workspace(manifest, build, subdir, project_root)
        return self.interpret_package(manifest, build, subdir, project_root)

    def interpret_package(self, manifest: Manifest, build: builder.Builder, subdir: str, project_root: T.Optional[str]) -> mparser.CodeBlockNode:
        # Build an AST for this package
        ast: T.List[mparser.BaseNode] = []
        if project_root:
            ws = self.workspaces[project_root]
            member = ws.packages_to_member[manifest.package.name]
            pkg = ws.packages[member]
        else:
            pkg, cached = self._fetch_package_from_manifest(manifest)
            if not cached:
                # This is an entry point, always enable the 'default' feature.
                # FIXME: We should have a Meson option similar to `cargo build --no-default-features`
                self._enable_feature(pkg, 'default')
            ast += self._create_project(pkg.manifest.package.name, pkg, build)
            ast.append(build.assign(build.function('import', [build.string('rust')]), 'rust'))
        ast += self._create_package(pkg, build, subdir)
        return build.block(ast)

    def _create_package(self, pkg: PackageState, build: builder.Builder, subdir: str) -> T.List[mparser.BaseNode]:
        ast: T.List[mparser.BaseNode] = [
            build.assign(build.array([build.string(f) for f in pkg.features]), 'features'),
            build.function('message', [
                build.string('Enabled features:'),
                build.identifier('features'),
            ]),
        ]
        ast += self._create_dependencies(pkg, build)
        ast += self._create_meson_subdir(build)
        ast += self._create_env_args(pkg, build, subdir)
        ast.append(build.assign(build.array([build.string(arg) for arg in self._lints_to_args(pkg)]), 'lint_args'))

        if pkg.manifest.lib:
            crate_type = pkg.manifest.lib.crate_type
            if 'dylib' in crate_type and 'cdylib' in crate_type:
                raise MesonException('Cannot build both dylib and cdylib due to file name conflict')
            if 'proc-macro' in crate_type:
                ast.extend(self._create_lib(pkg, build, 'proc-macro', shared=True))
            if any(x in crate_type for x in ['lib', 'rlib', 'dylib']):
                ast.extend(self._create_lib(pkg, build, 'rust',
                                            static=('lib' in crate_type or 'rlib' in crate_type),
                                            shared='dylib' in crate_type))
            if any(x in crate_type for x in ['staticlib', 'cdylib']):
                ast.extend(self._create_lib(pkg, build, 'c',
                                            static='staticlib' in crate_type,
                                            shared='cdylib' in crate_type))

        return ast

    def interpret_workspace(self, workspace: Workspace, build: builder.Builder, subdir: str, project_root: T.Optional[str]) -> mparser.CodeBlockNode:
        ws = self._get_workspace(workspace, subdir)
        name = os.path.dirname(subdir)
        subprojects_dir = os.path.join(subdir, 'subprojects')
        self.environment.wrap_resolver.load_and_merge(subprojects_dir, T.cast('SubProject', name))
        ast: T.List[mparser.BaseNode] = []
        if not ws.required_members:
            if ws.workspace.default_members:
                for member in ws.workspace.default_members:
                    self._require_workspace_member(ws, member)
            elif ws.workspace.root_package:
                self._require_workspace_member(ws, '.')
            else:
                for member in ws.workspace.members:
                    self._require_workspace_member(ws, member)

        # Call subdir() for each required member of the workspace. The order is
        # important, if a member depends on another member, that member must be
        # processed first.
        processed_members: T.Dict[str, PackageState] = {}

        def _process_member(member: str) -> None:
            if member in processed_members:
                return
            pkg = ws.packages[member]
            for depname in pkg.required_deps:
                dep = pkg.manifest.dependencies[depname]
                if dep.path:
                    dep_member = os.path.normpath(os.path.join(pkg.ws_member, dep.path))
                    _process_member(dep_member)
            if member == '.':
                ast.extend(self._create_package(pkg, build, subdir))
            else:
                ast.append(build.function('subdir', [build.string(member)]))
            processed_members[member] = pkg

        ast.append(build.assign(build.function('import', [build.string('rust')]), 'rust'))
        for member in ws.required_members:
            _process_member(member)
        if not project_root:
            ast = self._create_project(name, processed_members.get('.'), build) + ast

        return build.block(ast)

    def _load_workspace_member(self, ws: WorkspaceState, m: str) -> None:
        m = os.path.normpath(m)
        # Load member's manifest
        m_subdir = os.path.join(ws.subdir, m)
        manifest_ = self._load_manifest(m_subdir, ws.workspace, m)
        assert isinstance(manifest_, Manifest)
        self._add_workspace_member(manifest_, ws, m)

    def _add_workspace_member(self, manifest_: Manifest, ws: WorkspaceState, m: str) -> None:
        if m in ws.packages:
            return
        pkg = PackageState(manifest_, ws_subdir=ws.subdir, ws_member=m)
        ws.packages[m] = pkg
        ws.packages_to_member[manifest_.package.name] = m

    def _get_workspace(self, workspace: Workspace, subdir: str) -> WorkspaceState:
        ws = self.workspaces.get(subdir)
        if ws:
            return ws
        ws = WorkspaceState(workspace, subdir)
        for m in workspace.members:
            self._load_workspace_member(ws, m)
        if workspace.root_package:
            self._add_workspace_member(workspace.root_package, ws, '.')
        self.workspaces[subdir] = ws
        return ws

    def _require_workspace_member(self, ws: WorkspaceState, member: str) -> PackageState:
        member = os.path.normpath(member)
        pkg = ws.packages[member]
        if member not in ws.required_members:
            self._prepare_package(pkg)
            ws.required_members.append(member)
        return pkg

    def _fetch_package(self, package_name: str, api: str) -> PackageState:
        key = PackageKey(package_name, api)
        pkg = self.packages.get(key)
        if pkg:
            return pkg
        meson_depname = _dependency_name(package_name, api)
        return self._fetch_package_from_subproject(package_name, meson_depname)

    def _fetch_package_from_subproject(self, package_name: str, meson_depname: str) -> PackageState:
        subp_name, _ = self.environment.wrap_resolver.find_dep_provider(meson_depname)
        if subp_name is None:
            # If Cargo.lock has a different version, this could be a resolution
            # bug, but maybe also a version mismatch?  I am not sure yet...
            similar_deps = [pkg.subproject
                            for pkg in self.cargolock.named(package_name)]
            if similar_deps:
                similar_msg = f'Cargo.lock provides: {", ".join(similar_deps)}.'
            else:
                similar_msg = 'Cargo.lock does not contain this crate name.'
            raise MesonException(f'Dependency {meson_depname!r} not found in any wrap files or Cargo.lock; {similar_msg} This could be a Meson bug, please report it.')

        subdir, _ = self.environment.wrap_resolver.resolve(subp_name)
        subprojects_dir = os.path.join(subdir, 'subprojects')
        self.environment.wrap_resolver.load_and_merge(subprojects_dir, T.cast('SubProject', meson_depname))
        manifest = self._load_manifest(subdir)
        downloaded = \
            subp_name in self.environment.wrap_resolver.wraps and \
            self.environment.wrap_resolver.wraps[subp_name].type is not None

        if isinstance(manifest, Workspace):
            ws = self._get_workspace(manifest, subdir)
            member = ws.packages_to_member[package_name]
            pkg = self._require_workspace_member(ws, member)
            return pkg

        key = PackageKey(package_name, version.api(manifest.package.version))
        pkg = self.packages.get(key)
        if pkg:
            return pkg
        pkg = PackageState(manifest, downloaded)
        self.packages[key] = pkg
        self._prepare_package(pkg)
        return pkg

    def _fetch_package_from_manifest(self, manifest: Manifest) -> T.Tuple[PackageState, bool]:
        key = PackageKey(manifest.package.name, version.api(manifest.package.version))
        pkg = self.packages.get(key)
        if pkg:
            return pkg, True
        pkg = PackageState(manifest, downloaded=False)
        self.packages[key] = pkg
        self._prepare_package(pkg)
        return pkg, False

    def _prepare_package(self, pkg: PackageState) -> None:
        # Merge target specific dependencies that are enabled
        cfgs = self._get_cfgs(MachineChoice.HOST)
        for condition, dependencies in pkg.manifest.target.items():
            if cfg.eval_cfg(condition, cfgs):
                pkg.manifest.dependencies.update(dependencies)
        # Fetch required dependencies recursively.
        for depname, dep in pkg.manifest.dependencies.items():
            if not dep.optional:
                self._add_dependency(pkg, depname)

    def _dep_package(self, pkg: PackageState, dep: Dependency) -> PackageState:
        if dep.path:
            if not pkg.ws_subdir:
                raise MesonException("path dependencies only supported inside workspaces")
            ws = self.workspaces[pkg.ws_subdir]
            dep_member = os.path.normpath(os.path.join(pkg.ws_member, dep.path))
            self._load_workspace_member(ws, dep_member)
            dep_pkg = self._require_workspace_member(ws, dep_member)
        elif dep.git:
            _, _, directory = _parse_git_url(dep.git, dep.branch)
            dep_pkg = self._fetch_package_from_subproject(dep.package, directory)
        else:
            # From all available versions from Cargo.lock, pick the most recent
            # satisfying the constraints
            if self.cargolock:
                cargo_lock_pkgs = self.cargolock.named(dep.package)
            else:
                cargo_lock_pkgs = []
            for cargo_pkg in cargo_lock_pkgs:
                if all(version_compare(cargo_pkg.version, v) for v in dep.meson_version):
                    dep.update_version(f'={cargo_pkg.version}')
                    break
            else:
                if not dep.meson_version:
                    raise MesonException(f'Cannot determine version of cargo package {dep.package}')
            dep_pkg = self._fetch_package(dep.package, dep.api)
        if not dep.version:
            dep.update_version(f'={dep_pkg.manifest.package.version}')
        return dep_pkg

    def _load_manifest(self, subdir: str, workspace: T.Optional[Workspace] = None, member_path: str = '') -> T.Union[Manifest, Workspace]:
        manifest_ = self.manifests.get(subdir)
        if not manifest_:
            path = os.path.join(self.environment.source_dir, subdir)
            filename = os.path.join(path, 'Cargo.toml')
            self.build_def_files.append(filename)
            raw_manifest = T.cast('raw.Manifest', load_toml(filename))
            if 'workspace' in raw_manifest:
                manifest_ = Workspace.from_raw(raw_manifest, path)
            elif 'package' in raw_manifest:
                manifest_ = Manifest.from_raw(raw_manifest, path, workspace, member_path)
            else:
                raise MesonException(f'{subdir}/Cargo.toml does not have [package] or [workspace] section')
            self.manifests[subdir] = manifest_
        return manifest_

    def _add_dependency(self, pkg: PackageState, depname: str) -> None:
        if depname in pkg.required_deps:
            return
        dep = pkg.manifest.dependencies.get(depname)
        if not dep:
            # It could be build/dev/target dependency. Just ignore it.
            return
        pkg.required_deps.add(depname)
        dep_pkg = self._dep_package(pkg, dep)
        if dep.default_features:
            self._enable_feature(dep_pkg, 'default')
        for f in dep.features:
            self._enable_feature(dep_pkg, f)
        for f in pkg.optional_deps_features[depname]:
            self._enable_feature(dep_pkg, f)

    def _enable_feature(self, pkg: PackageState, feature: str) -> None:
        if feature in pkg.features:
            return
        pkg.features.add(feature)
        # A feature can also be a dependency.
        if feature in pkg.manifest.dependencies:
            self._add_dependency(pkg, feature)
        # Recurse on extra features and dependencies this feature pulls.
        # https://doc.rust-lang.org/cargo/reference/features.html#the-features-section
        for f in pkg.manifest.features.get(feature, []):
            if '/' in f:
                depname, dep_f = f.split('/', 1)
                if depname[-1] == '?':
                    depname = depname[:-1]
                    if depname in pkg.required_deps:
                        dep = pkg.manifest.dependencies[depname]
                        dep_pkg = self._dep_package(pkg, dep)
                        self._enable_feature(dep_pkg, dep_f)
                    else:
                        # This feature will be enabled only if that dependency
                        # is later added.
                        pkg.optional_deps_features[depname].add(dep_f)
                else:
                    self._add_dependency(pkg, depname)
                    dep = pkg.manifest.dependencies.get(depname)
                    if dep:
                        dep_pkg = self._dep_package(pkg, dep)
                        self._enable_feature(dep_pkg, dep_f)
            elif f.startswith('dep:'):
                self._add_dependency(pkg, f[4:])
            else:
                self._enable_feature(pkg, f)

    def has_check_cfg(self, machine: MachineChoice) -> bool:
        if not self.environment.is_cross_build():
            machine = MachineChoice.HOST
        rustc = T.cast('RustCompiler', self.environment.coredata.compilers[machine]['rust'])
        return rustc.has_check_cfg

    @functools.lru_cache(maxsize=None)
    def _get_cfgs(self, machine: MachineChoice) -> T.Dict[str, str]:
        if not self.environment.is_cross_build():
            machine = MachineChoice.HOST
        rustc = T.cast('RustCompiler', self.environment.coredata.compilers[machine]['rust'])
        cfgs = rustc.get_cfgs().copy()
        rustflags = self.environment.coredata.get_external_args(machine, 'rust')
        rustflags_i = iter(rustflags)
        for i in rustflags_i:
            if i == '--cfg':
                cfgs.append(next(rustflags_i))
        return dict(self._split_cfg(i) for i in cfgs)

    @staticmethod
    def _split_cfg(cfg: str) -> T.Tuple[str, str]:
        pair = cfg.split('=', maxsplit=1)
        value = pair[1] if len(pair) > 1 else ''
        if value and value[0] == '"':
            value = value[1:-1]
        return pair[0], value

    def _lints_to_args(self, pkg: PackageState) -> T.List[str]:
        args = []
        has_check_cfg = self.has_check_cfg(MachineChoice.HOST)
        for lint in pkg.manifest.lints:
            args.extend(lint.to_arguments(has_check_cfg))
        if has_check_cfg:
            for feature in pkg.manifest.features:
                if feature != 'default':
                    args.append('--check-cfg')
                    args.append(f'cfg(feature,values("{feature}"))')
        return args

    def _create_project(self, name: str, pkg: T.Optional[PackageState], build: builder.Builder) -> T.List[mparser.BaseNode]:
        """Create the project() function call

        :param pkg: The package to generate from
        :param build: The AST builder
        :return: a list nodes
        """
        args: T.List[mparser.BaseNode] = [
            build.string(name),
            build.string('rust'),
        ]
        kwargs: T.Dict[str, mparser.BaseNode] = {
            # Always assume that the generated meson is using the latest features
            # This will warn when when we generate deprecated code, which is helpful
            # for the upkeep of the module
            'meson_version': build.string(f'>= {coredata.stable_version}'),
        }
        if not pkg:
            return [
                build.function('project', args, kwargs),
            ]

        default_options: T.Dict[str, mparser.BaseNode] = {}
        if pkg.downloaded:
            default_options['warning_level'] = build.string('0')

        kwargs.update({
            'version': build.string(pkg.manifest.package.version),
            'default_options': build.dict({build.string(k): v for k, v in default_options.items()}),
        })
        if pkg.manifest.package.license:
            kwargs['license'] = build.string(pkg.manifest.package.license)
        elif pkg.manifest.package.license_file:
            kwargs['license_files'] = build.string(pkg.manifest.package.license_file)

        return [build.function('project', args, kwargs)]

    def _create_dependencies(self, pkg: PackageState, build: builder.Builder) -> T.List[mparser.BaseNode]:
        ast: T.List[mparser.BaseNode] = []
        for depname in pkg.required_deps:
            dep = pkg.manifest.dependencies[depname]
            dep_pkg = self._dep_package(pkg, dep)
            ast += self._create_dependency(dep_pkg, dep, build)
        ast.append(build.assign(build.array([]), 'system_deps_args'))
        for name, sys_dep in pkg.manifest.system_dependencies.items():
            if sys_dep.enabled(pkg.features):
                ast += self._create_system_dependency(name, sys_dep, build)
        return ast

    def _create_system_dependency(self, name: str, dep: SystemDependency, build: builder.Builder) -> T.List[mparser.BaseNode]:
        # TODO: handle feature_overrides
        kw = {
            'version': build.array([build.string(s) for s in dep.meson_version]),
            'required': build.bool(not dep.optional),
        }
        varname = f'{fixup_meson_varname(name)}_system_dep'
        cfg = f'system_deps_have_{fixup_meson_varname(name)}'
        return [
            build.assign(
                build.function(
                    'dependency',
                    [build.string(dep.name)],
                    kw,
                ),
                varname,
            ),
            build.if_(
                build.method('found', build.identifier(varname)), build.block([
                    build.plusassign(
                        build.array([build.string('--cfg'), build.string(cfg)]),
                        'system_deps_args'
                    ),
                ])
            ),
        ]

    def _create_dependency(self, pkg: PackageState, dep: Dependency, build: builder.Builder) -> T.List[mparser.BaseNode]:
        version_ = dep.meson_version or [pkg.manifest.package.version]
        kw = {
            'version': build.array([build.string(s) for s in version_]),
        }
        # Lookup for this dependency with the features we want in default_options kwarg.
        #
        # However, this subproject could have been previously configured with a
        # different set of features. Cargo collects the set of features globally
        # but Meson can only use features enabled by the first call that triggered
        # the configuration of that subproject.
        #
        # Verify all features that we need are actually enabled for that dependency,
        # otherwise abort with an error message. The user has to set the corresponding
        # option manually with -Dxxx-rs:feature-yyy=true, or the main project can do
        # that in its project(..., default_options: ['xxx-rs:feature-yyy=true']).
        return [
            # xxx_dep = dependency('xxx', version : ...)
            build.assign(
                build.function(
                    'dependency',
                    [build.string(_dependency_name(dep.package, dep.api))],
                    kw,
                ),
                _dependency_varname(dep),
            ),
            # actual_features = xxx_dep.get_variable('features', default_value : '').split(',')
            build.assign(
                build.method(
                    'split',
                    build.method(
                        'get_variable',
                        build.identifier(_dependency_varname(dep)),
                        [build.string('features')],
                        {'default_value': build.string('')}
                    ),
                    [build.string(',')],
                ),
                'actual_features'
            ),
            # needed_features = [f1, f2, ...]
            # foreach f : needed_features
            #   if f not in actual_features
            #     error()
            #   endif
            # endforeach
            build.assign(build.array([build.string(f) for f in pkg.features]), 'needed_features'),
            build.foreach(['f'], build.identifier('needed_features'), build.block([
                build.if_(build.not_in(build.identifier('f'), build.identifier('actual_features')), build.block([
                    build.function('error', [
                        build.string('Dependency'),
                        build.string(_dependency_name(dep.package, dep.api)),
                        build.string('previously configured with features'),
                        build.identifier('actual_features'),
                        build.string('but need'),
                        build.identifier('needed_features'),
                    ])
                ]))
            ])),
        ]

    def _create_meson_subdir(self, build: builder.Builder) -> T.List[mparser.BaseNode]:
        # Allow Cargo subprojects to add extra Rust args in meson/meson.build file.
        # This is used to replace build.rs logic.

        # extra_args = []
        # extra_deps = []
        # fs = import('fs')
        # if fs.is_dir('meson')
        #  subdir('meson')
        # endif
        return [
            build.assign(build.array([]), _extra_args_varname()),
            build.assign(build.array([]), _extra_deps_varname()),
            build.assign(build.function('import', [build.string('fs')]), 'fs'),
            build.if_(build.method('is_dir', build.identifier('fs'), [build.string('meson')]),
                      build.block([build.function('subdir', [build.string('meson')])]))
        ]

    def _pkg_common_env(self, pkg: PackageState, subdir: str) -> T.Dict[str, str]:
        # Common variables for build.rs and crates
        # https://doc.rust-lang.org/cargo/reference/environment-variables.html
        # OUT_DIR is the directory where build.rs generate files. In our case,
        # it's the directory where meson/meson.build places generated files.
        out_dir = os.path.join(self.environment.build_dir, subdir, 'meson')
        os.makedirs(out_dir, exist_ok=True)
        version_arr = pkg.manifest.package.version.split('.')
        version_arr += [''] * (4 - len(version_arr))
        return {
            'OUT_DIR': out_dir,
            'CARGO_MANIFEST_DIR': os.path.join(self.environment.source_dir, subdir),
            'CARGO_MANIFEST_PATH': os.path.join(self.environment.source_dir, subdir, 'Cargo.toml'),
            'CARGO_PKG_VERSION': pkg.manifest.package.version,
            'CARGO_PKG_VERSION_MAJOR': version_arr[0],
            'CARGO_PKG_VERSION_MINOR': version_arr[1],
            'CARGO_PKG_VERSION_PATCH': version_arr[2],
            'CARGO_PKG_VERSION_PRE': version_arr[3],
            'CARGO_PKG_AUTHORS': ','.join(pkg.manifest.package.authors),
            'CARGO_PKG_NAME': pkg.manifest.package.name,
            # FIXME: description can contain newlines which breaks ninja.
            #'CARGO_PKG_DESCRIPTION': pkg.manifest.package.description or '',
            'CARGO_PKG_HOMEPAGE': pkg.manifest.package.homepage or '',
            'CARGO_PKG_REPOSITORY': pkg.manifest.package.repository or '',
            'CARGO_PKG_LICENSE': pkg.manifest.package.license or '',
            'CARGO_PKG_LICENSE_FILE': pkg.manifest.package.license_file or '',
            'CARGO_PKG_RUST_VERSION': pkg.manifest.package.rust_version or '',
            'CARGO_PKG_README': pkg.manifest.package.readme or '',
        }

    def _create_env_args(self, pkg: PackageState, build: builder.Builder, subdir: str) -> T.List[mparser.BaseNode]:
        host_rustc = T.cast('RustCompiler', self.environment.coredata.compilers[MachineChoice.HOST]['rust'])
        enable_env_set_args = host_rustc.enable_env_set_args()
        if enable_env_set_args is None:
            return [build.assign(build.array([]), 'env_args')]
        # https://doc.rust-lang.org/cargo/reference/environment-variables.html#environment-variables-cargo-sets-for-crates
        env_dict = self._pkg_common_env(pkg, subdir)
        env_dict.update({
            'CARGO_CRATE_NAME': fixup_meson_varname(pkg.manifest.package.name),
            #FIXME: TODO
            #CARGO_BIN_NAME
            #CARGO_BIN_EXE_<name>
            #CARGO_PRIMARY_PACKAGE
            #CARGO_TARGET_TMPDIR
        })
        env_args: T.List[mparser.BaseNode] = [build.string(a) for a in enable_env_set_args]
        for k, v in env_dict.items():
            env_args += [build.string('--env-set'), build.string(f'{k}={v}')]
        return [build.assign(build.array(env_args), 'env_args')]

    def _create_lib(self, pkg: PackageState, build: builder.Builder,
                    lib_type: Literal['rust', 'c', 'proc-macro'],
                    static: bool = False, shared: bool = False) -> T.List[mparser.BaseNode]:
        dependencies: T.List[mparser.BaseNode] = []
        dependency_map: T.Dict[mparser.BaseNode, mparser.BaseNode] = {}
        for name in pkg.required_deps:
            dep = pkg.manifest.dependencies[name]
            dependencies.append(build.identifier(_dependency_varname(dep)))
            if name != dep.package:
                dep_pkg = self._dep_package(pkg, dep)
                dep_lib_name = _library_name(dep_pkg.manifest.lib.name, dep_pkg.manifest.package.api)
                dependency_map[build.string(dep_lib_name)] = build.string(name)
        for name, sys_dep in pkg.manifest.system_dependencies.items():
            if sys_dep.enabled(pkg.features):
                dependencies.append(build.identifier(f'{fixup_meson_varname(name)}_system_dep'))

        rust_args: T.List[mparser.BaseNode] = [
            build.identifier('features_args'),
            build.identifier(_extra_args_varname()),
            build.identifier('system_deps_args'),
            build.identifier('env_args'),
            build.identifier('lint_args'),
        ]

        dependencies.append(build.identifier(_extra_deps_varname()))

        override_options: T.Dict[mparser.BaseNode, mparser.BaseNode] = {
            build.string('rust_std'): build.string(pkg.manifest.package.edition),
        }

        posargs: T.List[mparser.BaseNode] = [
            build.string(_library_name(pkg.manifest.lib.name, pkg.manifest.package.api, lib_type)),
            build.string(pkg.manifest.lib.path),
        ]

        kwargs: T.Dict[str, mparser.BaseNode] = {
            'dependencies': build.array(dependencies),
            'rust_dependency_map': build.dict(dependency_map),
            'rust_args': build.array(rust_args),
            'override_options': build.dict(override_options),
        }

        depname_suffix = '' if lib_type == 'c' else '-rs'
        depname = _dependency_name(pkg.manifest.package.name, pkg.manifest.package.api, depname_suffix)

        lib: mparser.BaseNode
        if lib_type == 'proc-macro':
            lib = build.method('proc_macro', build.identifier('rust'), posargs, kwargs)
        else:
            if static and shared:
                target_type = 'both_libraries'
            else:
                target_type = 'shared_library' if shared else 'static_library'

            kwargs['rust_abi'] = build.string(lib_type)
            lib = build.function(target_type, posargs, kwargs)

        features_args: T.List[mparser.BaseNode] = []
        for f in pkg.features:
            features_args += [build.string('--cfg'), build.string(f'feature="{f}"')]

        # features_args = ['--cfg', 'feature="f1"', ...]
        # lib = xxx_library()
        # dep = declare_dependency()
        # meson.override_dependency()
        return [
            build.assign(build.array(features_args), 'features_args'),
            build.assign(lib, 'lib'),
            build.assign(
                build.function(
                    'declare_dependency',
                    kw={
                        'link_with': build.identifier('lib'),
                        'variables': build.dict({
                            build.string('features'): build.string(','.join(pkg.features)),
                        }),
                        'version': build.string(pkg.manifest.package.version),
                    },
                ),
                'dep'
            ),
            build.method(
                'override_dependency',
                build.identifier('meson'),
                [
                    build.string(depname),
                    build.identifier('dep'),
                ],
            ),
        ]


def _parse_git_url(url: str, branch: T.Optional[str] = None) -> T.Tuple[str, str, str]:
    if url.startswith('git+'):
        url = url[4:]
    parts = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parts.query)
    query_branch = query['branch'][0] if 'branch' in query else ''
    branch = branch or query_branch
    revision = parts.fragment or branch
    directory = os.path.basename(parts.path)
    if directory.endswith('.git'):
        directory = directory[:-4]
    if branch:
        directory += f'-{branch}'
    url = urllib.parse.urlunparse(parts._replace(params='', query='', fragment=''))
    return url, revision, directory


def load_cargo_lock(filename: str, subproject_dir: str) -> T.Optional[CargoLock]:
    """ Convert Cargo.lock into a list of wraps """

    # Map directory -> PackageDefinition, to avoid duplicates. Multiple packages
    # can have the same source URL, in that case we have a single wrap that
    # provides multiple dependency names.
    if os.path.exists(filename):
        toml = load_toml(filename)
        raw_cargolock = T.cast('raw.CargoLock', toml)
        cargolock = CargoLock.from_raw(raw_cargolock)
        wraps: T.Dict[str, PackageDefinition] = {}
        for package in cargolock.package:
            meson_depname = _dependency_name(package.name, version.api(package.version))
            if package.source is None:
                # This is project's package, or one of its workspace members.
                pass
            elif package.source == 'registry+https://github.com/rust-lang/crates.io-index':
                checksum = package.checksum
                if checksum is None:
                    checksum = cargolock.metadata[f'checksum {package.name} {package.version} ({package.source})']
                url = f'https://crates.io/api/v1/crates/{package.name}/{package.version}/download'
                directory = f'{package.name}-{package.version}'
                if directory not in wraps:
                    wraps[directory] = PackageDefinition.from_values(meson_depname, subproject_dir, 'file', {
                        'directory': directory,
                        'source_url': url,
                        'source_filename': f'{directory}.tar.gz',
                        'source_hash': checksum,
                        'method': 'cargo',
                    })
                wraps[directory].add_provided_dep(meson_depname)
            elif package.source.startswith('git+'):
                url, revision, directory = _parse_git_url(package.source)
                if directory not in wraps:
                    wraps[directory] = PackageDefinition.from_values(directory, subproject_dir, 'git', {
                        'url': url,
                        'revision': revision,
                        'method': 'cargo',
                    })
                wraps[directory].add_provided_dep(meson_depname)
            else:
                mlog.warning(f'Unsupported source URL in {filename}: {package.source}')
        cargolock.wraps = {w.name: w for w in wraps.values()}
        return cargolock
    return None
