# SPDX-license-identifier: Apache-2.0
# Copyright © 2020-2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
import collections
import textwrap
import typing as T

import toml

from .. import mlog
from ..mesonlib import MesonException, version_compare_many
from ..optinterpreter import is_invalid_name
from .nodebuilder import ObjectBuilder, NodeBuilder
from .cfg_parser import parse as cfg_parser
from . import cfg_builder

if T.TYPE_CHECKING:
    from .. import mparser
    from ..backend.backends import Backend
    from ..build import Build
    from ..environment import Environment

    try:
        from typing import TypedDict
    except AttributeError:
        from typing_extensions import TypedDict

    try:
        from typing import Literal
    except AttributeError:
        from typing_extensions import Literal

    _PackageDict = TypedDict(
        '_PackageDict',
        {
            # These are required by crates.io
            'name': str,
            'version': str,          # should be in X.Y.Z format
            'authors': T.List[str],  # XXX: Might be str | List[str]
            'edition': Literal['2015', '2018'],
            'description': str,

            # These are not
            'documentation': str,
            'readme': str,
            'homepage': str,
            'license': str,                  # We should get either a license or a license-file
            'license-file': str,
            'workspace': str,                # XXX: figure out what this means
            'build': str,                    # If this is set we can't use this method, you'll have to write a meson.build
            'links': str,                    # a system library to link to
            'include': T.List[str],          # for dist packaging
            'exclude': T.List[str],          # for dist packaging
            'publish': bool,                 # should be safe to ignore
            'metadata': T.Dict[str, T.Any],  # should also be safe to ignore, unless we want a meson field
            'default-run': str,              # should be safe to ignore
            'autobins': bool,                # These all have to do with target autodiscovery, and we'll need to deal with them
            'autoexamples': bool,
            'autotests': bool,
            'autobenches': bool,
        },
        total=False,
    )

    # For more complicated dependencies.
    _DependencyDict = TypedDict(
        '_DependencyDict',
        {
            # Tags for using a git based crate
            'git': str,     # the path to the repo, required
            'branch': str,  # the branch to use
            'tag': str,     # A tag to use
            'rev': str,     # A commitish to use

            # General attributes
            'version': str,    # this is the same mini language as if a string is provided
            'path': str ,      # when using a local crate
            'optional': bool,  # whether or not this dependency is required
            'package': str,    # I *think* this allow renaming the outputs of the crate

            # Special attributes for handling dependency specific features
            'default-features': bool,
            'features': T.List[str],
        },
        total=False,
    )

    # Information in the [[bin]] section
    _TargetEntry = TypedDict(
        '_TargetEntry',
        {
            'name': str,
            'path': str,
            'test': bool,
            'doctest': bool,
            'bench': bool,
            'doc': bool,
            'proc-macro': bool,
            'harness': bool,
            'edition': Literal['2015', '2018'],
            'crate-type': T.List[Literal['bin', 'lib', 'dylib', 'staticlib', 'cdylib', 'rlib', 'proc-macro']],
            'required-features': T.List[str],
        },
        total=False
    )

    class TargetDict(TypedDict):

        dependencies: T.Dict[str, T.Union[str, _DependencyDict]]


    # Type information for a Cargo.toml manifest file.
    ManifestDict = TypedDict(
        'ManifestDict',
        {
            'package': _PackageDict,
            'lib': _TargetEntry,
            'bin': T.List[_TargetEntry],
            'test': T.List[_TargetEntry],
            'features': T.Dict[str, T.List[str]],
            'dependencies': T.Dict[str, T.Union[str, _DependencyDict]],
            'dev-dependencies': T.Dict[str, T.Union[str, _DependencyDict]],
            'target': T.Dict[str, TargetDict],
        },
        total=False,
    )


def cargo_version_to_meson_version(req_string: str) -> T.List[str]:
    """Takes a cargo version string, and creates a list list of meson version strings.

    Cargo has a couple of syntaxes:
    ^ (caret), which means at least this version, but not the next major version:
    ~ (tilde), which is hard to explain
    * (wildcard), which is globbing (a bare * is not allowed)
    comparison handling, like meson's <, >, >=

    Carot handling:

    >>> cargo_version_to_meson_version('^1')
    ['>= 1.0.0', '< 2.0.0']
    >>> cargo_version_to_meson_version('^2.3')
    ['>= 2.3.0', '< 3.0.0']
    >>> cargo_version_to_meson_version('^0.3.1')
    ['>= 0.3.1', '< 0.4.0']
    >>> cargo_version_to_meson_version('^0.0.1')
    ['>= 0.0.1', '< 0.0.2']
    >>> cargo_version_to_meson_version('^0.0')
    ['>= 0.0.0', '< 0.1.0']
    >>> cargo_version_to_meson_version('^0')
    ['>= 0.0.0', '< 1.0.0']

    Tilde handling:

    >>> cargo_version_to_meson_version('~1.2.3')
    ['>= 1.2.3', '< 1.3.0']
    >>> cargo_version_to_meson_version('~1.2')
    ['>= 1.2.0', '< 1.3.0']
    >>> cargo_version_to_meson_version('~1')
    ['>= 1.0.0', '< 2.0.0']

    Wildcard handling:

    >>> cargo_version_to_meson_version('*')
    []
    >>> cargo_version_to_meson_version('1.*')
    ['>= 1.0.0', '< 2.0.0']
    >>> cargo_version_to_meson_version('1.2.*')
    ['>= 1.2.0', '< 1.3.0']

    Comparison:
    >>> cargo_version_to_meson_version('>= 1.0.0')
    ['>= 1.0.0']
    >>> cargo_version_to_meson_version('>= 1')
    ['>= 1']
    >>> cargo_version_to_meson_version('= 1')
    ['== 1']
    >>> cargo_version_to_meson_version('< 2.3')
    ['< 2.3']

    Multiple:
    >>> cargo_version_to_meson_version('>= 1.0.0, < 1.5')
    ['>= 1.0.0', '< 1.5']
    """
    # cargo
    requirements = [r.strip() for r in req_string.split(',')]
    final: T.List[str] = []

    def split(raw: str) -> T.Tuple[int, T.Optional[int], T.Optional[int]]:
        _major, *v = raw.split('.')
        major = int(_major)
        minor = int(v[0]) if v else None
        patch = int(v[1]) if len(v) == 2 else None
        return major, minor, patch

    for r in requirements:
        if r.startswith('^'):
            major, minor, patch = split(r.lstrip('^'))
            final.append(f'>= {major}.{minor or 0}.{patch or 0}')
            if major:
                final.append(f'< {major + 1}.0.0')
            elif minor:
                final.append(f'< 0.{minor + 1}.0')
            elif patch:
                final.append(f'< 0.0.{patch + 1}')
            else:
                # This handles cases of ^0[.0], which are odd
                assert major == 0 and (minor is None or minor == 0) and (patch is None)
                if minor is not None:
                    final.append(f'< 0.1.0')
                else:
                    final.append(f'< 1.0.0')
        elif r.startswith('~'):
            major, minor, patch = split(r.lstrip('~'))
            final.append(f'>= {major}.{minor or 0}.{patch or 0}')
            if patch is not None or minor is not None:
                final.append(f'< {major}.{minor + 1}.0')
            else:
                final.append(f'< {major + 1}.0.0')
        elif r.endswith('*'):
            # crates.io doesn't allow this, but let's be a bit permissive
            if r == '*':
                continue
            major, minor, patch = split(r.rstrip('.*'))
            assert patch is None

            final.append(f'>= {major}.{minor or 0}.{patch or 0}')
            if minor is not None:
                final.append(f'< {major}.{minor + 1}.0')
            else:
                final.append(f'< {major + 1}.0.0')
        else:
            assert r.startswith(('<', '>', '=')), r
            if r.startswith('='):
                # meson uses ==, but cargo uses =
                final.append(f'={r}')
            else:
                final.append(r)
    return final


class ManifestInterpreter:

    """Takes a cargo manifest.toml and creates AST to consume as a subproject.

    All targets are always marked as `build_by_default : false`, this allows
    meson to intelligently build only the required targets, and not build
    anything we don't actually need (like binaries we may not use).
    """

    def __init__(self, build: 'Build', build_dir: Path, src_dir: Path, install_prefix: Path,
                 env: 'Environment', backend: 'Backend', features: T.Set[str],
                 version: T.List[str], default_options: bool):
        self.build = build
        # TODO: The builddir needs to be modfied to take the version requirements and
        # options into account
        self.build_dir = build_dir
        # TODO: The src_dir needs to consider the version, and if it needs src_dir-version
        self.src_dir = src_dir
        self.install_prefix = install_prefix
        self.environment = env
        self.backend = backend
        self.requested_features = features
        self.default_options = default_options
        self.required_version = version
        manifest_file = self.src_dir / 'Cargo.toml'
        self.manifest_file = str(manifest_file)
        with manifest_file.open('r') as f:
            self.manifest = T.cast('ManifestDict', toml.load(f))

        # If the version in the subdir doesn't match, then we need to try to find
        # a subproject source that does match.
        actual_version = self.manifest['package']['version']
        if not version_compare_many(actual_version, self.required_version)[0]:
            for g in (self.src_dir.parent.glob(f'{self.src_dir.stem}-*')):
                # XXX: it might be better to read the version out of the toml
                v = g.stem.split('-')[-1]
                if version_compare_many(v, self.required_version):
                    self.src_dir = g
                    # XXX: uhhh, this is a hack, maybe?
                    self.build_dir = self.build_dir.parent / g
                    manifest_file = self.src_dir / 'Cargo.toml'
                    self.manifest_file = str(manifest_file)
                    with manifest_file.open('r') as f:
                        self.manifest = T.cast('ManifestDict', toml.load(f))
                    break
            else:
                raise MesonException(
                    f'Cannot find subproject source for {self.src_dir.stem} to '
                    f'satisfy version requirements {self.required_version}.')

        # All features enabled in this subproject
        self.features: T.List[str] = []

        # Map features that this crate turns on for its subprojects
        self.subproject_features: T.DefaultDict[str, T.Set[str]] = collections.defaultdict(set)

        # A mapping between a feature and the dependencies that are needed to
        # enable it.
        self.features_to_deps: T.Dict[str, T.List[str]] = {}

    def __parse_lib(self, builder: NodeBuilder) -> None:
        """"Look for a a lib if there is one.

        Fortunately cargo only allows one lib in a manifest, this means for
        us that we don't have to worry quite as much about the auto discover.
        """
        lib = self.manifest.get('lib', {})
        if lib or (self.src_dir / 'src' / 'lib.rs').exists():
            # We always call the library lib, for simplicity
            name = lib.get('name', self.manifest['package']['name']).replace('-', '_')
            with builder.assignment_builder('lib') as asbuilder:
                with asbuilder.function_builder('build_target') as fbuilder:
                    # The name of the lib is not required, if it is not provided it
                    # should be the name of the package with any - replaced with _
                    # https://doc.rust-lang.org/cargo/reference/cargo-targets.html#the-name-field
                    fbuilder.positional(name)
                    fbuilder.positional(lib.get('path', 'src/lib.rs'))

                    # XXX: this is the same hack as described below
                    if lib.get('proc-macro', False) or lib.get('crate-type', ['rlib'])[0] in {'dylib', 'cdylib', 'proc-macro'}:
                        fbuilder.keyword('target_type', 'shared_library')
                    else:
                        # This scoops up the "lib" type as well. Meson very
                        # much prefers that things be explicit, not
                        # implicit. Therefore we assume that "lib" means ""
                        fbuilder.keyword('target_type', 'static_library')

                    # Lib as of 2020-10-23, means rlib. We want to enforce that
                    # XXX: this is wrong, crate-type is a list, and cargo will
                    # generate one target of each type listed. I messed this up
                    # early on, so for now we just have a hack to work around this
                    if lib.get('proc-macro', False):
                        fbuilder.keyword('rust_crate_type', 'proc-macro')
                    elif lib.get('crate-type', ['lib'])[0] == 'lib':
                        fbuilder.keyword('rust_crate_type', 'rlib')
                    else:
                        assert len(lib['crate-type']) == 1
                        fbuilder.keyword('rust_crate_type', lib['crate-type'][0])

                    # Proc macros must not have versions in them
                    if not lib.get('proc-macro', False):
                        fbuilder.keyword('version', self.manifest['package']['version'])

                    edition = lib.get('edition', self.manifest['package'].get('edition'))
                    if edition:
                        fbuilder.keyword('override_options', [f'rust_std={edition}'])

                    # We always call the list of dependencies "dependencies",
                    # if there are dependencies we can add them. There could
                    # be an empty dependencies section, so account for that
                    if self.manifest.get('dependencies') or self.manifest.get('target') or self.manifest['package'].get('links'):
                        fbuilder.keyword('dependencies', builder.id('dependencies'))

                    # Always mark everything as build by default false, that way meson will
                    # only compile the things we actually need
                    fbuilder.keyword('build_by_default', False)

            with builder.assignment_builder('dep') as asbuilder:
                with asbuilder.function_builder('declare_dependency') as fbuilder:
                    fbuilder.keyword('link_with', builder.id('lib'))
                    # It may not be strictly necessary to link with all of the
                    # dependencies, but it is in some cases.
                    if self.manifest.get('dependencies') or self.manifest.get('target'):
                        fbuilder.keyword('dependencies', builder.id('dependencies'))

            # XXX: This should be True by default, but I've run into crates
            # that hardcode their names in the rust files, not sure what to do.
            if lib.get('test', False):
                with builder.object_builder('rust') as obuilder:
                    with obuilder.method_builder('test') as fbuilder:
                        fbuilder.positional('lib_test')
                        fbuilder.positional(builder.id('lib'))
                        try:
                            fbuilder.keyword('dependencies', builder.id('dev_dependencies'))
                        except MesonException:
                            pass

    def __emit_bins(self, builder: NodeBuilder) -> None:
        """Look for any binaries that need to be built.

        Cargo has two methods for this, autobins, and manual bins. Autobins
        stink from a meson point of view, because there's no way without a
        manual reconfigure to make them reliable, but they are *very* popular
        from the brief survey I did. The other option is manual bins. We
        support both, but manual bins are more reliable.
        """
        targets = self.__emit_exe_targets(builder, 'bin')

        # Create a unit test target unless that target specifically requested
        # not to have one
        no_tests = {b['name'] for b in self.manifest.get('bin', []) if not b.get('test', True)}
        for t in targets:
            if t in no_tests:
                continue

            with builder.object_builder('rust') as obuilder:
                with obuilder.method_builder('test') as fbuilder:
                    fbuilder.positional(f'{t}_test')
                    fbuilder.positional(builder.id(t))
                    try:
                        fbuilder.keyword('dependencies', builder.id('dev_dependencies'))
                    except MesonException:
                        pass

    def __emit_tests(self, builder: NodeBuilder) -> None:
        """Look for any test targets that need to be built.

        Additionally we need to create a standard (not rust module) test
        target for each binary we build. We call these `_integration_test`,
        so we don't have collisions with our unit tests.
        """
        targets = self.__emit_exe_targets(builder, 'test')
        for t in targets:
            with builder.function_builder('test') as fbuilder:
                fbuilder.positional(f'{t}_integration_test')
                fbuilder.positional(builder.id(t))
                try:
                    fbuilder.keyword('dependencies', builder.id('dev_dependencies'))
                except MesonException:
                    pass

    def __emit_exe_targets(self, builder: NodeBuilder, target: "Literal['bin', 'test']") -> T.List[str]:
        """Shared helper for all executable targets.

        Cargo has auto discovery (globing, bleh), and manual discover. We
        need to support both to successfully parse cargo manifests. This code
        is meant to be shared between the different type of binary targets.

        Returns a list of all of the targets it created for the caller to
        work with. This allows, for example, for the caller to create test
        cases.
        """
        def make_bin(name: str, source: str, edition: T.Optional[str] = None, unittest: bool = True) -> None:
            """Craete a single binary.
            """
            created_targets.append(name)
            with builder.assignment_builder(name) as asbuilder:
                with asbuilder.function_builder('executable') as fbuilder:
                    fbuilder.positional(name)
                    fbuilder.positional(source)
                    try:
                        fbuilder.keyword('link_with', builder.id('lib'))
                    except MesonException:
                        pass
                    try:
                        fbuilder.keyword('dependencies', builder.id('dev_dependencies'))
                    except MesonException:
                        pass
                    if edition:
                        fbuilder.keyword('override_options', [f'rust_std={edition}'])

                    # Always mark everything as build by default false, that way meson will
                    # only compile the things we actually need
                    fbuilder.keyword('build_by_default', False)

        package_edition: str = self.manifest['package'].get('edition', '2015')
        manual_targets = self.manifest.get(target, T.cast(T.List['_TargetEntry'], []))

        created_targets: T.List[str] = []
        # TODO: main.rs isn't supported?

        if self.manifest['package'].get(f'auto{target}s', package_edition == '2018' or not manual_targets):
            mlog.warning(textwrap.dedent(f'''\
                cargo is using auto{target}s, this is a form of globbing.
                ninja may not always detect that you need to reconfigure if
                you update cargo subprojects. In this case you will need to
                run `meson setup --reconfigure` manually.
                '''), once=True)

            paths: T.List[Path] = []
            if target == 'bin':
                main = self.src_dir / 'src' / 'main.rs'
                if main.exists():
                    paths.append(main.relative_to(self.src_dir))
            if target == 'bin':
                targetdir = self.src_dir / 'src' / 'bin'
            elif target == 'test':
                targetdir = self.src_dir / 'tests'
            if targetdir.is_dir():
                paths.extend([p.relative_to(self.src_dir) for p in targetdir.glob('*.rs')])

            for each in paths:
                name = each.with_suffix('').name.replace('-', '_')
                if name == 'test':
                    name = 'test_'
                # TODO: this needs a test
                if any(b['name'] == name for b in manual_targets):
                    continue
                make_bin(name, str(each), package_edition)

        # You can have both autodiscovered an manually discovered targets in
        # the same manifest
        for bin in manual_targets:
            edition = bin.get('edition', package_edition)
            make_bin(bin['name'], bin['path'], edition)

        return created_targets

    def __parse_features(self) -> None:
        """Parse cargo features.

        Cargo's features are basically akin to boolean option in meson.

        Cargo features do not map 1:1 with meson options, and we need to do
        some transformation to make them work. First, one uses a special
        "default" option to signal which options are on by default. Second,
        options are allowed to specify "If I'm on, then I need my subproject
        to have option X on."
        """
        for name, requirements in self.manifest.get('features', {}).items():
            if name == "default":
                continue

            # Sometimes cargo feature names are reserved in meson, we need to
            # convert those to somethign valid, we use name_
            if is_invalid_name(name):
                name = f'{name}_'

            new_reqs: T.List[str] = []
            for r in requirements:
                if '/' in r:
                    subp, opt = r.split('/')
                    self.subproject_features[subp].add(opt)
                    new_reqs.append(subp)
                else:
                    new_reqs.append(r)

            self.features.append(name)
            if new_reqs:
                self.features_to_deps[name] = new_reqs

    def __emit_features(self, opt_builder: NodeBuilder) -> None:
        """Write out features as options."""
        enabled: T.Set[str] = self.requested_features.copy()
        if self.default_options:
            enabled |= set(self.manifest.get('features', {}).get('default', []))

        for name in self.features:
            with opt_builder.function_builder('option') as fbuilder:
                fbuilder.positional(name)
                fbuilder.keyword('type', 'boolean')
                fbuilder.keyword('value', name in enabled)

    def __get_dependency(self, builder: NodeBuilder, name: str, disabler: bool = False) -> 'mparser.MethodNode':
        """Helper for getting a supbroject dependency."""
        obuilder = ObjectBuilder('rust', builder._builder)
        with obuilder.method_builder('subproject') as arbuilder:
            arbuilder.positional(name.replace('-', '_'))
            # Pass any features we required to be on to that subproject
            if self.subproject_features[name]:
                arbuilder.keyword('features', list(self.subproject_features[name]))
            if disabler:
                arbuilder.keyword('required', False)
        with obuilder.method_builder('get_variable') as arbuilder:
            arbuilder.positional('dep')  # we always use dep
            if disabler:
                arbuilder.positional(builder._builder.function('disabler'))
        return obuilder.finalize()

    def __emit_dependencies(self, builder: NodeBuilder) -> None:
        """Parse all of the dependencies

        Check all of the dependencies we need, create a "dependencies" array
        to hold each of them and populate it. The required dependencies are
        injected first, and then the create if nodes to add the optional ones
        only if needed.
        """
        with builder.assignment_builder('dependencies') as abuilder:
            with abuilder.array_builder() as arbuilder:
                for name, dep in self.manifest.get('dependencies', {}).items():
                    # If the dependency is required, go ahead and build the
                    # subproject call unconditionally
                    if isinstance(dep, str) or not dep.get('optional', False):
                        arbuilder.positional(self.__get_dependency(builder, name))

        # If we need to link with a system library, we'll first try a
        # dependency
        #
        # TODO: if that doesn't work, we need to fall back to adding a C
        # compiler and running c.find_library()
        if self.manifest['package'].get('links'):
            with builder.assignment_builder('link_library') as abuilder:
                with abuilder.function_builder('dependency') as argbuilder:
                    argbuilder.positional(self.manifest['package']['links'])
            with builder.plus_assignment_builder('dependencies') as pabuilder:
                pabuilder.reference('link_library')

        # If it's optional, then we need to check that the feature that
        # it depends on is available, then add it to the dependency array.
        for name, requires in self.features_to_deps.items():
            with builder.if_builder() as ifcbuilder:
                with ifcbuilder.if_builder() as ifbuilder:
                    with ifbuilder.condition_builder() as cbuilder:
                        with cbuilder.function_builder('get_option') as fbuilder:
                            fbuilder.positional(name)
                    with ifbuilder.body_builder() as bbuilder:
                        with bbuilder.plus_assignment_builder('dependencies') as pabuilder:
                            with pabuilder.array_builder() as arbuilder:
                                for name in requires:
                                    arbuilder.positional(self.__get_dependency(builder, name))

        # Next we need to check for target (platform) specific dependencies
        for condition, target in self.manifest.get('target', {}).items():
            if condition.startswith('cfg('):
                with builder.if_builder() as ifcbuilder:
                    with ifcbuilder.if_builder() as ifbuilder:
                        with ifbuilder.condition_builder() as cbuilder:
                            cfg_builder.build(cbuilder, cfg_parser(condition).root)
                        with ifbuilder.body_builder() as bbuilder:
                            with bbuilder.plus_assignment_builder('dependencies') as pabuilder:
                                with pabuilder.array_builder() as arbuilder:
                                    for name, dep in target['dependencies'].items():
                                        # If the dependency is required, go ahead and build the
                                        # subproject call unconditionally
                                        if isinstance(dep, str) or not dep.get('optional', False):
                                            arbuilder.positional(self.__get_dependency(builder, name))
            else:
                raise NotImplementedError(f'condition: {condition}')

    def __emit_dev_dependencies(self, builder: NodeBuilder) -> None:
        """Parse all dev-dependencies

        These are needed by tests, benchmarks, and examples, but are not
        propgated or used in building distributed binaries or libraries.
        """
        with builder.assignment_builder('dev_dependencies') as abuilder:
            with abuilder.array_builder() as arbuilder:
                for name, dep in self.manifest.get('dev-dependencies', {}).items():
                    # If the dependency is required, go ahead and build the
                    # subproject call unconditionally
                    if isinstance(dep, str) or not dep.get('optional', False):
                        arbuilder.positional(self.__get_dependency(builder, name, disabler=True))

    def __emit_enable_features(self, builder: NodeBuilder) -> None:
        """Emit the code to check each feature, and add it to the rust
        arguments if necessary.

        We use add_project_arguments() here, because it simplifies our code
        generation
        """
        for f in self.features:
            with builder.if_builder() as ifcbuilder:
                with ifcbuilder.if_builder() as ifbuilder:
                    with ifbuilder.condition_builder() as cbuilder:
                        with cbuilder.function_builder('get_option') as fbuilder:
                            fbuilder.positional(f)
                    with ifbuilder.body_builder() as bbuilder:
                        with bbuilder.function_builder('add_project_arguments') as fbuilder:
                            fbuilder.positional(['--cfg', f'feature="{f}"'])
                            fbuilder.keyword('language', 'rust')

    def parse(self) -> T.Tuple['mparser.CodeBlockNode', 'mparser.CodeBlockNode']:
        """Create a meson code node from a cargo manifest file

        This can then be fed back into the meson interpreter to create a
        "meson" project from the crate specification.
        """
        # Parse features and emit options. These are also needed by dependencies
        opt_builder = NodeBuilder(self.build_dir)
        self.__parse_features()
        self.__emit_features(opt_builder)

        builder = NodeBuilder(self.build_dir)

        # Create the meson project() function.
        #
        # Currently, we generate:
        # - name
        # - version
        # - license (only if the license is an SPDX string)
        default_options: T.List[str] = []
        with builder.function_builder('project') as fbuilder:
            fbuilder.positional(self.manifest['package']['name'].replace('-', '_'))
            fbuilder.positional(['rust'])
            fbuilder.keyword('version', self.manifest['package']['version'])
            if 'license' in self.manifest['package']:
                fbuilder.keyword('license', self.manifest['package']['license'])
            if 'edition' in self.manifest['package']:
                default_options.append(f'rust_std={self.manifest["package"]["edition"]}')
            if default_options:
                fbuilder.keyword('default_options', default_options)

        # Import the rust module
        #
        # This is needed in enough cases it makes sense to just always import
        # it, as it vaslty simplifes things.
        with builder.assignment_builder('rust') as abuilder:
            with abuilder.function_builder('import') as fbuilder:
                fbuilder.positional('unstable-rust')

        # Create a list of dependencies which will be added to the library (if
        # there is one).
        if self.manifest.get('dependencies') or self.manifest.get('target') or self.manifest['package'].get('links'):
            self.__emit_dependencies(builder)
        if self.manifest.get('dev-dependencies'):
            self.__emit_dev_dependencies(builder)

        # This needs to be called after dependencies
        self.__emit_enable_features(builder)

        # Look for libs first, becaue if there are libs, then bins need to link
        # with them.
        self.__parse_lib(builder)
        self.__emit_bins(builder)
        self.__emit_tests(builder)

        return builder.finalize(), opt_builder.finalize()
