# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2023 Intel Corporation

from __future__ import annotations
import unittest
import os
import tempfile
import textwrap
import typing as T

from mesonbuild.cargo import cfg
from mesonbuild.cargo.cfg import TokenType
from mesonbuild.cargo.interpreter import load_cargo_lock
from mesonbuild.cargo.manifest import Dependency, Lint, Manifest, Package, Workspace, validate_patch
from mesonbuild.cargo.toml import load_toml
from mesonbuild.cargo.version import api, cargo_parse, SemVer
from mesonbuild.mesonlib import MesonException


class CargoVersionTest(unittest.TestCase):

    def test_cargo_parse(self) -> None:
        # Each case is (cargo_requirement, accepted_versions, rejected_versions).
        # The conversion from Cargo to Meson constraints is opaque, so probe the
        # resulting predicate on versions around the boundaries.
        cases: T.List[T.Tuple[str, T.List[str], T.List[str]]] = [
            # Basic comparison requirements
            ('>= 1', ['1', '1.0', '1.5', '2'], ['0.9']),
            ('> 1', ['1.0.1', '1.5', '2'], ['0.9', '1']),
            ('= 1', ['1', '1.0', '1.0.0'], ['0.9', '1.0.1', '2']),
            ('< 1', ['0.9'], ['1', '1.0', '2']),
            # Trailing zeros in the bound: Meson's Version treats a shorter
            # prefix as < the same prefix with trailing zeros, so the >= bound
            # must be canonicalized to behave like Cargo (where 1 == 1.0 == 1.0.0).
            ('>= 1.0', ['1', '1.0', '1.0.0', '1.5'], ['0.9']),
            ('>= 1.0.0', ['1', '1.0', '1.0.0', '1.5'], ['0.9']),
            ('> 1.0', ['1.0.1', '1.5', '2'], ['0.9', '1', '1.0']),
            ('> 1.0.0', ['1.0.1', '1.5', '2'], ['0.9', '1', '1.0', '1.0.0']),
            # Cargo's <= must accept x.y.z, which Meson's <= would not
            ('<= 1', ['0.9', '1', '1.0', '1.5', '1.99'], ['2', '2.0']),
            ('<= 1.1', ['1.0', '1.1', '1.1.5'], ['1.2', '2']),
            ('<= 1.1.1', ['1.0', '1.1', '1.1.1'], ['1.1.2', '1.2']),

            # Tilde requirements
            ('~1', ['1', '1.5', '1.99'], ['0.9', '2']),
            ('~1.1', ['1.1', '1.1.5'], ['1.0', '1.2', '2']),
            ('~1.1.2', ['1.1.2', '1.1.5'], ['1.1.1', '1.2.0']),

            # Wildcards
            ('*', ['0.1', '1', '99.99'], []),
            ('1.*', ['1', '1.5'], ['0.9', '2']),
            ('2.3.*', ['2.3', '2.3.5'], ['2.2', '2.4']),

            # Unqualified
            ('2', ['2', '2.5'], ['1', '3']),
            ('2.4', ['2.4', '2.5'], ['2.3', '3']),
            ('2.4.5', ['2.4.5', '2.6'], ['2.4.4', '3']),
            ('0.0.0', ['0', '0.0.0', '0.0.5', '0.5'], ['1']),
            ('0.0', ['0', '0.5', '0.999'], ['1']),
            ('0', ['0', '0.5'], ['1']),
            ('0.0.5', ['0.0.5'], ['0.0.4', '0.0.6']),
            ('0.5.0', ['0.5.0', '0.5.5'], ['0.4.0', '0.6']),
            ('0.5', ['0.5', '0.5.5'], ['0.4', '0.6']),
            ('1.0.45', ['1.0.45', '1.5'], ['1.0.44', '2']),

            # Caret (equivalent to unqualified)
            ('^2', ['2', '2.5'], ['1', '3']),
            ('^2.4', ['2.4', '2.5'], ['2.3', '3']),
            ('^2.4.5', ['2.4.5', '2.6'], ['2.4.4', '3']),
            ('^1.0', ['1', '1.0', '1.0.0', '1.5'], ['0.9', '2']),
            ('^1.0.0', ['1', '1.0', '1.0.0', '1.5'], ['0.9', '2']),
            ('^0.0.0', ['0', '0.0.5'], ['1']),
            ('^0.0', ['0', '0.5'], ['1']),
            ('^0', ['0', '0.5'], ['1']),
            ('^0.0.5', ['0.0.5'], ['0.0.4', '0.0.6']),
            ('^0.5.0', ['0.5.0', '0.5.5'], ['0.4.0', '0.6']),
            ('^0.5', ['0.5', '0.5.5'], ['0.4', '0.6']),

            # Multiple requirements
            ('>= 1.2.3, < 1.4.7', ['1.2.3', '1.3.0'], ['1.2.2', '1.4.7', '1.5']),

            # Pre-releases are excluded unless a constraint itself names a
            # pre-release, even when otherwise in range.
            ('>= 1.0', ['1.0', '1.5', '2'], ['2.0-pre1', '1.5-pre1']),
            ('^1', ['1', '1.5'], ['1.5.0-pre', '2.0-pre']),
            # A pre-release bound enables pre-release matching and orders them.
            ('>= 1.0.0-alpha',
             ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-beta', '1.0.0', '1.5'],
             ['1.0.0-alph', '0.9']),
            ('>= 1.0.0-alpha, < 1.0.0',
             ['1.0.0-alpha', '1.0.0-beta', '1.0.0-rc.1'],
             ['1.0.0', '0.9']),
        ]

        for (cargo_req, accepted, rejected) in cases:
            check = cargo_parse(cargo_req)
            for ver in accepted:
                with self.subTest(req=cargo_req, ver=ver):
                    self.assertTrue(check(ver), f'{cargo_req!r} should accept {ver!r}')
            for ver in rejected:
                with self.subTest(req=cargo_req, ver=ver):
                    self.assertFalse(check(ver), f'{cargo_req!r} should reject {ver!r}')

    def test_semver_has_prerelease(self) -> None:
        self.assertTrue(SemVer('1.0.0-alpha').has_prerelease)
        self.assertFalse(SemVer('1.0.0').has_prerelease)
        self.assertFalse(SemVer('1.0.0+build.5').has_prerelease)

    def test_semver_parse(self) -> None:
        # Pre-release components parse into the version vector after a -1
        # sentinel; build metadata (after '+') is discarded.
        self.assertEqual(SemVer('1.2.3')._v, [1, 2, 3, 0])
        self.assertEqual(SemVer('1.0.0-alpha.1')._v, [1, 0, 0, -1, 'alpha', 1])
        self.assertEqual(SemVer('1.2.3-rc.1+exp.sha')._v, [1, 2, 3, -1, 'rc', 1])
        self.assertEqual(SemVer('1.0.0+build.5')._v, [1, 0, 0, 0])

        # numeric identifiers sort below alphanumeric ones, a larger set of fields
        # wins, and a release sorts above all of its pre-releases.
        # https://semver.org/#spec-item-11
        ordered = [
            '1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta',
            '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0',
        ]
        for lo, hi in zip(ordered, ordered[1:]):
            with self.subTest(lo=lo, hi=hi):
                self.assertLess(SemVer(lo), SemVer(hi))
                self.assertGreater(SemVer(hi), SemVer(lo))

        # Build metadata does not affect precedence.
        self.assertEqual(SemVer('1.0.0+build.5'), SemVer('1.0.0'))
        self.assertEqual(SemVer('1.2.3-rc.1+exp.sha'), SemVer('1.2.3-rc.1'))

    def test_api(self) -> None:
        cases: T.List[T.Tuple[str, str]] = [
            # Plain versions
            ('1.2.3', '1'),
            ('0.4.5', '0.4'),
            ('0.0.3', '0'),

            # Explicit operators
            ('1.*', '1'),
        ]
        for (data, expected) in cases:
            with self.subTest(data=data):
                self.assertEqual(api(data), expected)


class CargoCfgTest(unittest.TestCase):

    def test_lex(self) -> None:
        cases: T.List[T.Tuple[str, T.List[T.Tuple[TokenType, T.Optional[str]]]]] = [
            ('"unix"', [(TokenType.STRING, 'unix')]),
            ('unix', [(TokenType.IDENTIFIER, 'unix')]),
            ('not(unix)', [
                (TokenType.NOT, None),
                (TokenType.LPAREN, None),
                (TokenType.IDENTIFIER, 'unix'),
                (TokenType.RPAREN, None),
            ]),
            ('any(unix, windows)', [
                (TokenType.ANY, None),
                (TokenType.LPAREN, None),
                (TokenType.IDENTIFIER, 'unix'),
                (TokenType.COMMA, None),
                (TokenType.IDENTIFIER, 'windows'),
                (TokenType.RPAREN, None),
            ]),
            ('target_arch = "x86_64"', [
                (TokenType.IDENTIFIER, 'target_arch'),
                (TokenType.EQUAL, None),
                (TokenType.STRING, 'x86_64'),
            ]),
            ('all(target_arch = "x86_64", unix)', [
                (TokenType.ALL, None),
                (TokenType.LPAREN, None),
                (TokenType.IDENTIFIER, 'target_arch'),
                (TokenType.EQUAL, None),
                (TokenType.STRING, 'x86_64'),
                (TokenType.COMMA, None),
                (TokenType.IDENTIFIER, 'unix'),
                (TokenType.RPAREN, None),
            ]),
            ('cfg(windows)', [
                (TokenType.CFG, None),
                (TokenType.LPAREN, None),
                (TokenType.IDENTIFIER, 'windows'),
                (TokenType.RPAREN, None),
            ]),
        ]
        for data, expected in cases:
            with self.subTest():
                self.assertListEqual(list(cfg.lexer(data)), expected)

    def test_parse(self) -> None:
        cases = [
            ('target_os = "windows"', cfg.Equal(cfg.Identifier("target_os"), cfg.String("windows"))),
            ('target_arch = "x86"', cfg.Equal(cfg.Identifier("target_arch"), cfg.String("x86"))),
            ('target_family = "unix"', cfg.Equal(cfg.Identifier("target_family"), cfg.String("unix"))),
            ('any(target_arch = "x86", target_arch = "x86_64")',
                cfg.Any(
                    [
                        cfg.Equal(cfg.Identifier("target_arch"), cfg.String("x86")),
                        cfg.Equal(cfg.Identifier("target_arch"), cfg.String("x86_64")),
                    ])),
            ('all(target_arch = "x86", target_os = "linux")',
                cfg.All(
                    [
                        cfg.Equal(cfg.Identifier("target_arch"), cfg.String("x86")),
                        cfg.Equal(cfg.Identifier("target_os"), cfg.String("linux")),
                    ])),
            ('not(all(target_arch = "x86", target_os = "linux"))',
                cfg.Not(
                    cfg.All(
                        [
                            cfg.Equal(cfg.Identifier("target_arch"), cfg.String("x86")),
                            cfg.Equal(cfg.Identifier("target_os"), cfg.String("linux")),
                        ]))),
            ('cfg(all(any(target_os = "android", target_os = "linux"), any(custom_cfg)))',
                cfg.All([
                    cfg.Any([
                        cfg.Equal(cfg.Identifier("target_os"), cfg.String("android")),
                        cfg.Equal(cfg.Identifier("target_os"), cfg.String("linux")),
                    ]),
                    cfg.Any([
                        cfg.Identifier("custom_cfg"),
                    ]),
                ])),
        ]
        for data, expected in cases:
            with self.subTest():
                self.assertEqual(cfg.parse(iter(cfg.lexer(data))), expected)

    def test_eval_ir(self) -> None:
        d = {
            'target_os': 'unix',
            'unix': '',
        }
        cases = [
            ('target_os = "windows"', False),
            ('target_os = "unix"', True),
            ('doesnotexist = "unix"', False),
            ('not(target_os = "windows")', True),
            ('any(target_os = "windows", target_arch = "x86_64")', False),
            ('any(target_os = "windows", target_os = "unix")', True),
            ('all(target_os = "windows", target_os = "unix")', False),
            ('all(not(target_os = "windows"), target_os = "unix")', True),
            ('any(unix, windows)', True),
            ('all()', True),
            ('any()', False),
            ('cfg(unix)', True),
            ('cfg(windows)', False),
        ]
        for data, expected in cases:
            with self.subTest():
                value = cfg.eval_cfg(data, d)
                self.assertEqual(value, expected)

class CargoLockTest(unittest.TestCase):
    def test_wraps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'Cargo.lock')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(textwrap.dedent('''\
                    version = 3
                    [[package]]
                    name = "foo"
                    version = "0.1"
                    source = "registry+https://github.com/rust-lang/crates.io-index"
                    checksum = "8a30b2e23b9e17a9f90641c7ab1549cd9b44f296d3ccbf309d2863cfe398a0cb"
                    [[package]]
                    name = "bar"
                    version = "0.1"
                    source = "git+https://github.com/gtk-rs/gtk-rs-core?branch=0.19#23c5599424cc75ec66618891c915d9f490f6e4c2"
                    [[package]]
                    name = "member"
                    version = "0.1"
                    source = "git+https://github.com/gtk-rs/gtk-rs-core?branch=0.19#23c5599424cc75ec66618891c915d9f490f6e4c2"
                    '''))
            cargolock = load_cargo_lock(filename, 'subprojects')
            wraps = cargolock.wraps
            self.assertEqual(len(wraps), 2)
            self.assertEqual(wraps['foo-0.1-rs'].name, 'foo-0.1-rs')
            self.assertEqual(wraps['foo-0.1-rs'].directory, 'foo-0.1')
            self.assertEqual(wraps['foo-0.1-rs'].type, 'file')
            self.assertEqual(wraps['foo-0.1-rs'].get('method'), 'cargo')
            self.assertEqual(wraps['foo-0.1-rs'].get('source_url'), 'https://crates.io/api/v1/crates/foo/0.1/download')
            self.assertEqual(wraps['foo-0.1-rs'].get('source_hash'), '8a30b2e23b9e17a9f90641c7ab1549cd9b44f296d3ccbf309d2863cfe398a0cb')
            self.assertEqual(wraps['gtk-rs-core-0.19'].name, 'gtk-rs-core-0.19')
            self.assertEqual(wraps['gtk-rs-core-0.19'].directory, 'gtk-rs-core-0.19')
            self.assertEqual(wraps['gtk-rs-core-0.19'].type, 'git')
            self.assertEqual(wraps['gtk-rs-core-0.19'].get('method'), 'cargo')
            self.assertEqual(wraps['gtk-rs-core-0.19'].get('url'), 'https://github.com/gtk-rs/gtk-rs-core')
            self.assertEqual(wraps['gtk-rs-core-0.19'].get('revision'), '23c5599424cc75ec66618891c915d9f490f6e4c2')
            self.assertEqual(list(wraps['gtk-rs-core-0.19'].provided_deps), ['gtk-rs-core-0.19', 'bar-0.1-rs', 'member-0.1-rs'])

class CargoTomlTest(unittest.TestCase):
    CARGO_TOML_1 = textwrap.dedent('''\
        [package]
        name = "mandelbrot"
        version = "0.1.0"
        authors = ["Sebastian Dröge <sebastian@centricular.com>"]
        edition = "2018"
        license = "GPL-3.0"

        [package.metadata.docs.rs]
        all-features = true
        rustc-args = [
            "--cfg",
            "docsrs",
        ]
        rustdoc-args = [
            "--cfg",
            "docsrs",
            "--generate-link-to-definition",
        ]

        [dependencies]
        gtk = { package = "gtk4", version = "0.9" }
        num-complex = "0.4"
        rayon = "1.0"
        once_cell = "1"
        async-channel = "2.1"
        zerocopy = { version = "0.7", features = ["derive"] }

        [lints.rust]
        unknown_lints = "allow"
        unexpected_cfgs = { level = "deny", check-cfg = [ 'cfg(MESON)' ] }

        [lints.clippy]
        pedantic = {level = "warn", priority = -1}

        [dev-dependencies.gir-format-check]
        version = "^0.1"
        ''')

    CARGO_TOML_2 = textwrap.dedent('''\
        [package]
        name = "pango"
        edition = "2021"
        rust-version = "1.70"
        version = "0.20.4"
        authors = ["The gtk-rs Project Developers"]

        [package.metadata.system-deps.pango]
        name = "pango"
        version = "1.40"

        [package.metadata.system-deps.pango.v1_42]
        version = "1.42"

        [lib]
        name = "pango"

        [[test]]
        name = "check_gir"
        path = "tests/check_gir.rs"

        [features]
        v1_42 = ["pango-sys/v1_42"]
        v1_44 = [
            "v1_42",
            "pango-sys/v1_44",
        ]
    ''')

    CARGO_TOML_3 = textwrap.dedent('''\
        [package]
        name = "bits"
        edition = "2021"
        rust-version = "1.70"
        version = "0.1.0"

        [lib]
        proc-macro = true
        crate-type = ["lib"] # ignored
    ''')

    CARGO_TOML_WS = textwrap.dedent('''\
        [workspace]
        resolver = "2"
        members = ["tutorial"]

        [workspace.package]
        version = "0.14.0-alpha.1"
        repository = "https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs"
        edition = "2021"
        rust-version = "1.83"

        [workspace.dependencies]
        glib = { path = "glib" }
        gtk = { package = "gtk4", version = "0.9" }
        once_cell = "1.0"
        syn = { version = ">=1, <3", features = ["parse"] }

        [workspace.lints.rust]
        warnings = "deny"
    ''')

    def test_cargo_toml_ws_lints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_WS)
            workspace_toml = load_toml(fname)

        workspace = Workspace.from_raw(workspace_toml, tmpdir)
        pkg = Manifest.from_raw({'package': {'name': 'foo'},
                                 'lints': {'workspace': True}}, 'Cargo.toml', workspace)
        lints = pkg.lints
        self.assertEqual(lints[0].name, 'warnings')
        self.assertEqual(lints[0].level, 'deny')
        self.assertEqual(lints[0].priority, 0)

        pkg = Manifest.from_raw({'package': {'name': 'bar'}}, 'Cargo.toml', workspace)
        self.assertEqual(pkg.lints, [])

    def test_cargo_toml_ws_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_WS)
            workspace_toml = load_toml(fname)

        workspace = Workspace.from_raw(workspace_toml, tmpdir)
        pkg = Package.from_raw({'name': 'foo', 'version': {'workspace': True}}, workspace)
        self.assertEqual(pkg.name, 'foo')
        self.assertEqual(pkg.version, '0.14.0-alpha.1')
        self.assertEqual(pkg.edition, '2015')
        self.assertEqual(pkg.repository, None)

    def test_update_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_WS)
            workspace_toml = load_toml(fname)

        workspace = Workspace.from_raw(workspace_toml, tmpdir)
        dep = Dependency.from_raw('syn', {'workspace': True, 'features': ['full']}, 'member', workspace)
        self.assertEqual(dep.api, '1')
        dep.update_version('=2.0.113')
        self.assertEqual(dep.api, '2')

    def test_cargo_toml_ws_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_WS)
            workspace_toml = load_toml(fname)

        workspace = Workspace.from_raw(workspace_toml, tmpdir)
        dep = Dependency.from_raw('glib', {'workspace': True}, 'member', workspace)
        self.assertEqual(dep.package, 'glib')
        self.assertEqual(dep.version, '')
        self.assertTrue(dep.accepts_version('9999'))
        self.assertEqual(dep.path, os.path.join('..', 'glib'))
        self.assertEqual(dep.features, [])

        dep = Dependency.from_raw('gtk', {'workspace': True}, 'member', workspace)
        self.assertEqual(dep.package, 'gtk4')
        self.assertEqual(dep.version, '0.9')
        self.assertTrue(dep.accepts_version('0.9'))
        self.assertFalse(dep.accepts_version('0.10'))
        self.assertEqual(dep.api, '0.9')
        self.assertEqual(dep.features, [])

        dep = Dependency.from_raw('once_cell', {'workspace': True, 'optional': True}, 'member', workspace)
        self.assertEqual(dep.package, 'once_cell')
        self.assertEqual(dep.version, '1.0')
        self.assertTrue(dep.accepts_version('1.0'))
        self.assertTrue(dep.accepts_version('1.23'))
        self.assertFalse(dep.accepts_version('2.0'))
        self.assertFalse(dep.accepts_version('2.0-pre1'))
        self.assertEqual(dep.api, '1')
        self.assertEqual(dep.features, [])
        self.assertTrue(dep.optional)

        dep = Dependency.from_raw('syn', {'workspace': True, 'features': ['full']}, 'member', workspace)
        self.assertEqual(dep.package, 'syn')
        self.assertEqual(dep.version, '>=1, <3')
        self.assertTrue(dep.accepts_version('1.0'))
        self.assertTrue(dep.accepts_version('2.0'))
        self.assertFalse(dep.accepts_version('3.0'))
        self.assertEqual(dep.api, '1')
        self.assertEqual(sorted(set(dep.features)), ['full', 'parse'])

    def test_cargo_toml_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_1)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(manifest.package.name, 'mandelbrot')
        self.assertEqual(manifest.package.version, '0.1.0')
        self.assertEqual(manifest.package.authors[0], 'Sebastian Dröge <sebastian@centricular.com>')
        self.assertEqual(manifest.package.edition, '2018')
        self.assertEqual(manifest.package.license, 'GPL-3.0')

        print(manifest.package.metadata)
        self.assertEqual(len(manifest.package.metadata), 1)

    def test_cargo_toml_lints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_1)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(len(manifest.lints), 3)
        self.assertEqual(manifest.lints[0].name, 'clippy::pedantic')
        self.assertEqual(manifest.lints[0].level, 'warn')
        self.assertEqual(manifest.lints[0].priority, -1)
        self.assertEqual(manifest.lints[0].check_cfg, None)

        self.assertEqual(manifest.lints[1].name, 'unknown_lints')
        self.assertEqual(manifest.lints[1].level, 'allow')
        self.assertEqual(manifest.lints[1].priority, 0)
        self.assertEqual(manifest.lints[1].check_cfg, None)

        self.assertEqual(manifest.lints[2].name, 'unexpected_cfgs')
        self.assertEqual(manifest.lints[2].level, 'deny')
        self.assertEqual(manifest.lints[2].priority, 0)
        self.assertEqual(manifest.lints[2].check_cfg, ['cfg(MESON)'])

    def test_cargo_toml_lints_to_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_1)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(manifest.lints[0].to_arguments(False), ['-W', 'clippy::pedantic'])
        self.assertEqual(manifest.lints[0].to_arguments(True), ['-W', 'clippy::pedantic'])
        self.assertEqual(manifest.lints[1].to_arguments(False), ['-A', 'unknown_lints'])
        self.assertEqual(manifest.lints[1].to_arguments(True), ['-A', 'unknown_lints'])
        self.assertEqual(manifest.lints[2].to_arguments(False), ['-D', 'unexpected_cfgs'])
        self.assertEqual(manifest.lints[2].to_arguments(True),
                         ['-D', 'unexpected_cfgs', '--check-cfg', 'cfg(MESON)'])

    def test_cargo_toml_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_1)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(len(manifest.dependencies), 6)
        self.assertEqual(manifest.dependencies['gtk'].package, 'gtk4')
        self.assertEqual(manifest.dependencies['gtk'].version, '0.9')
        self.assertTrue(manifest.dependencies['gtk'].accepts_version('0.9'))
        self.assertFalse(manifest.dependencies['gtk'].accepts_version('0.10'))
        self.assertEqual(manifest.dependencies['gtk'].api, '0.9')
        self.assertEqual(manifest.dependencies['num-complex'].package, 'num-complex')
        self.assertEqual(manifest.dependencies['num-complex'].version, '0.4')
        self.assertTrue(manifest.dependencies['num-complex'].accepts_version('0.4'))
        self.assertFalse(manifest.dependencies['num-complex'].accepts_version('0.5'))
        self.assertEqual(manifest.dependencies['rayon'].package, 'rayon')
        self.assertEqual(manifest.dependencies['rayon'].version, '1.0')
        self.assertTrue(manifest.dependencies['rayon'].accepts_version('1.0'))
        self.assertTrue(manifest.dependencies['rayon'].accepts_version('1.23'))
        self.assertFalse(manifest.dependencies['rayon'].accepts_version('2.0'))
        self.assertFalse(manifest.dependencies['rayon'].accepts_version('2.0-pre1'))
        self.assertEqual(manifest.dependencies['rayon'].api, '1')
        self.assertEqual(manifest.dependencies['once_cell'].package, 'once_cell')
        self.assertEqual(manifest.dependencies['once_cell'].version, '1')
        self.assertTrue(manifest.dependencies['once_cell'].accepts_version('1.0'))
        self.assertTrue(manifest.dependencies['once_cell'].accepts_version('1.23'))
        self.assertFalse(manifest.dependencies['once_cell'].accepts_version('2.0'))
        self.assertFalse(manifest.dependencies['once_cell'].accepts_version('2.0-pre1'))
        self.assertEqual(manifest.dependencies['once_cell'].api, '1')
        self.assertEqual(manifest.dependencies['async-channel'].package, 'async-channel')
        self.assertEqual(manifest.dependencies['async-channel'].version, '2.1')
        self.assertFalse(manifest.dependencies['async-channel'].accepts_version('2.0'))
        self.assertTrue(manifest.dependencies['async-channel'].accepts_version('2.1'))
        self.assertTrue(manifest.dependencies['async-channel'].accepts_version('2.23'))
        self.assertFalse(manifest.dependencies['async-channel'].accepts_version('2.0'))
        self.assertFalse(manifest.dependencies['async-channel'].accepts_version('2.0-pre1'))
        self.assertEqual(manifest.dependencies['async-channel'].api, '2')
        self.assertEqual(manifest.dependencies['zerocopy'].package, 'zerocopy')
        self.assertEqual(manifest.dependencies['zerocopy'].version, '0.7')
        self.assertTrue(manifest.dependencies['zerocopy'].accepts_version('0.7'))
        self.assertFalse(manifest.dependencies['zerocopy'].accepts_version('0.8'))
        self.assertEqual(manifest.dependencies['zerocopy'].features, ['derive'])
        self.assertEqual(manifest.dependencies['zerocopy'].api, '0.7')

        self.assertEqual(len(manifest.dev_dependencies), 1)
        self.assertEqual(manifest.dev_dependencies['gir-format-check'].package, 'gir-format-check')
        self.assertEqual(manifest.dev_dependencies['gir-format-check'].version, '^0.1')
        self.assertTrue(manifest.dev_dependencies['gir-format-check'].accepts_version('0.1'))
        self.assertFalse(manifest.dev_dependencies['gir-format-check'].accepts_version('0.2'))
        self.assertEqual(manifest.dev_dependencies['gir-format-check'].api, '0.1')

    def test_cargo_toml_proc_macro(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_3)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(manifest.lib.name, 'bits')
        self.assertEqual(manifest.lib.crate_type, ['proc-macro'])
        self.assertEqual(manifest.lib.path, 'src/lib.rs')

        del manifest_toml['lib']['crate-type']
        manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')
        self.assertEqual(manifest.lib.name, 'bits')
        self.assertEqual(manifest.lib.crate_type, ['proc-macro'])
        self.assertEqual(manifest.lib.path, 'src/lib.rs')

    def test_cargo_toml_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_2)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(manifest.lib.name, 'pango')
        self.assertEqual(manifest.lib.crate_type, ['lib'])
        self.assertEqual(manifest.lib.path, 'src/lib.rs')
        self.assertEqual(manifest.lib.test, True)
        self.assertEqual(manifest.lib.doctest, True)
        self.assertEqual(manifest.lib.bench, True)
        self.assertEqual(manifest.lib.doc, True)
        self.assertEqual(manifest.lib.harness, True)
        self.assertEqual(manifest.lib.edition, '2021')
        self.assertEqual(manifest.lib.required_features, [])
        self.assertEqual(manifest.lib.plugin, False)

        self.assertEqual(len(manifest.test), 1)
        self.assertEqual(manifest.test[0].name, 'check_gir')
        self.assertEqual(manifest.test[0].crate_type, ['bin'])
        self.assertEqual(manifest.test[0].path, 'tests/check_gir.rs')
        self.assertEqual(manifest.lib.path, 'src/lib.rs')
        self.assertEqual(manifest.test[0].test, True)
        self.assertEqual(manifest.test[0].doctest, True)
        self.assertEqual(manifest.test[0].bench, False)
        self.assertEqual(manifest.test[0].doc, False)
        self.assertEqual(manifest.test[0].harness, True)
        self.assertEqual(manifest.test[0].edition, '2021')
        self.assertEqual(manifest.test[0].required_features, [])
        self.assertEqual(manifest.test[0].plugin, False)

    def test_cargo_toml_system_deps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_2)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertIn('system-deps', manifest.package.metadata)

        self.assertEqual(len(manifest.system_dependencies), 1)
        self.assertEqual(manifest.system_dependencies['pango'].name, 'pango')
        self.assertEqual(manifest.system_dependencies['pango'].version, '1.40')
        self.assertEqual(manifest.system_dependencies['pango'].meson_version, ['>=1.40'])
        self.assertEqual(manifest.system_dependencies['pango'].optional, False)
        self.assertEqual(manifest.system_dependencies['pango'].feature, None)

        self.assertEqual(len(manifest.system_dependencies['pango'].feature_overrides), 1)
        self.assertEqual(manifest.system_dependencies['pango'].feature_overrides['v1_42'], {'version': '1.42'})

    def test_cargo_toml_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, 'Cargo.toml')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(self.CARGO_TOML_2)
            manifest_toml = load_toml(fname)
            manifest = Manifest.from_raw(manifest_toml, 'Cargo.toml')

        self.assertEqual(len(manifest.features), 3)
        self.assertEqual(manifest.features['v1_42'], ['pango-sys/v1_42'])
        self.assertEqual(manifest.features['v1_44'], ['v1_42', 'pango-sys/v1_44'])
        self.assertEqual(manifest.features['default'], [])

    def test_validate_patch(self) -> None:
        # packages_to_member values are normalized with os.path.normpath (see
        # _load_workspace_member), so do the same here
        resolved = {
            'cxx': '.',
            'cxx-build': os.path.normpath('gen/build'),
            'member': os.path.normpath('vendor/member'),
        }

        patch = {'crates-io': {
            'cxx': {'path': '.'},
            'cxx-build': {'path': 'gen/build'},
            'member': {'version': '1', 'path': 'vendor/member'},
        }}

        # Empty or absent [patch]
        self.assertFalse(list(validate_patch(None, resolved)))
        self.assertFalse(list(validate_patch({}, resolved)))

        # Invalid [patch] tables
        self.assertTrue(list(validate_patch({'crates-io': {}, 'https://example.com': {}}, resolved)))
        self.assertTrue(list(validate_patch({'crates-io': 'nonsense'}, resolved)))
        self.assertTrue(list(validate_patch('nonsense', resolved)))

        # Invalid entries
        self.assertTrue(list(validate_patch({'crates-io': {'cxx': {'git': 'https://example.com'}}}, resolved)))
        self.assertTrue(list(validate_patch({'crates-io': {'cxx': '1.0'}}, resolved)))

        # Unknown crate
        self.assertTrue(list(validate_patch({'crates-io': {'unknown': {'path': 'foo'}}}, resolved)))

        # The only entries that don't warn point at a package that Meson already builds
        self.assertFalse(list(validate_patch(patch, resolved)))
        self.assertTrue(list(validate_patch({'crates-io': {'cxx-build': {'path': 'elsewhere'}}}, resolved)))
