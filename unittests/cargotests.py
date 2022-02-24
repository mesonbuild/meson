# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2023 Intel Corporation

from __future__ import annotations
import unittest
import typing as T

from mesonbuild.cargo import builder, cfg
from mesonbuild.cargo.cfg import TokenType
from mesonbuild.cargo.version import convert


class CargoVersionTest(unittest.TestCase):

    def test_cargo_to_meson(self) -> None:
        cases: T.List[T.Tuple[str, T.List[str]]] = [
            # Basic requirements
            ('>= 1', ['>= 1']),
            ('> 1', ['> 1']),
            ('= 1', ['= 1']),
            ('< 1', ['< 1']),
            ('<= 1', ['<= 1']),

            # tilde tests
            ('~1', ['>= 1', '< 2']),
            ('~1.1', ['>= 1.1', '< 1.2']),
            ('~1.1.2', ['>= 1.1.2', '< 1.2.0']),

            # Wildcards
            ('*', []),
            ('1.*', ['>= 1', '< 2']),
            ('2.3.*', ['>= 2.3', '< 2.4']),

            # Unqualified
            ('2', ['>= 2', '< 3']),
            ('2.4', ['>= 2.4', '< 3']),
            ('2.4.5', ['>= 2.4.5', '< 3']),
            ('0.0.0', ['< 1']),
            ('0.0', ['< 1']),
            ('0', ['< 1']),
            ('0.0.5', ['>= 0.0.5', '< 0.0.6']),
            ('0.5.0', ['>= 0.5', '< 0.6']),
            ('0.5', ['>= 0.5', '< 0.6']),

            # Caret (Which is the same as unqualified)
            ('^2', ['>= 2', '< 3']),
            ('^2.4', ['>= 2.4', '< 3']),
            ('^2.4.5', ['>= 2.4.5', '< 3']),
            ('^0.0.0', ['< 1']),
            ('^0.0', ['< 1']),
            ('^0', ['< 1']),
            ('^0.0.5', ['>= 0.0.5', '< 0.0.6']),
            ('^0.5.0', ['>= 0.5', '< 0.6']),
            ('^0.5', ['>= 0.5', '< 0.6']),

            # Multiple requirements
            ('>= 1.2.3, < 1.4.7', ['>= 1.2.3', '< 1.4.7']),
        ]

        for (data, expected) in cases:
            with self.subTest():
                self.assertListEqual(convert(data), expected)


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
        ]
        for data, expected in cases:
            with self.subTest():
                self.assertListEqual(list(cfg.lexer(data)), expected)

    def test_parse(self) -> None:
        cases = [
            ('target_os = "windows"', cfg.Equal('', cfg.Identifier('', "target_os"), cfg.String('', "windows"))),
            ('target_arch = "x86"', cfg.Equal('', cfg.Identifier('', "target_arch"), cfg.String('', "x86"))),
            ('target_family = "unix"', cfg.Equal('', cfg.Identifier('', "target_family"), cfg.String('', "unix"))),
            ('any(target_arch = "x86", target_arch = "x86_64")',
                cfg.Any(
                    '', [
                        cfg.Equal('', cfg.Identifier('', "target_arch"), cfg.String('', "x86")),
                        cfg.Equal('', cfg.Identifier('', "target_arch"), cfg.String('', "x86_64")),
                    ])),
            ('all(target_arch = "x86", target_os = "linux")',
                cfg.All(
                    '', [
                        cfg.Equal('', cfg.Identifier('', "target_arch"), cfg.String('', "x86")),
                        cfg.Equal('', cfg.Identifier('', "target_os"), cfg.String('', "linux")),
                    ])),
            ('not(all(target_arch = "x86", target_os = "linux"))',
                cfg.Not(
                    '',
                    cfg.All(
                        '', [
                            cfg.Equal('', cfg.Identifier('', "target_arch"), cfg.String('', "x86")),
                            cfg.Equal('', cfg.Identifier('', "target_os"), cfg.String('', "linux")),
                        ]))),
        ]
        for data, expected in cases:
            with self.subTest():
                self.assertEqual(cfg.parse(iter(cfg.lexer(data)), ''), expected)

    def test_ir_to_meson(self) -> None:
        HOST_MACHINE = builder.identifier('host_machine', '')

        cases = [
            ('target_os = "windows"',
             builder.equal(builder.method('system', HOST_MACHINE),
                           builder.string('windows', ''))),
            ('target_arch = "x86"',
             builder.equal(builder.method('cpu_family', HOST_MACHINE),
                           builder.string('x86', ''))),
            ('target_family = "unix"',
             builder.equal(builder.method('system', HOST_MACHINE),
                           builder.string('unix', ''))),
            ('not(target_arch = "x86")',
             builder.not_(builder.equal(
                builder.method('cpu_family', HOST_MACHINE),
                builder.string('x86', '')), '')),
            ('any(target_arch = "x86", target_arch = "x86_64")',
             builder.or_(
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86', '')),
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86_64', '')))),
            ('any(target_arch = "x86", target_arch = "x86_64", target_arch = "aarch64")',
             builder.or_(
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86', '')),
                builder.or_(
                    builder.equal(builder.method('cpu_family', HOST_MACHINE),
                                  builder.string('x86_64', '')),
                    builder.equal(builder.method('cpu_family', HOST_MACHINE),
                                  builder.string('aarch64', ''))))),
            ('all(target_arch = "x86", target_arch = "x86_64")',
             builder.and_(
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86', '')),
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86_64', '')))),
            ('all(target_arch = "x86", target_arch = "x86_64", target_arch = "aarch64")',
             builder.and_(
                builder.equal(builder.method('cpu_family', HOST_MACHINE),
                              builder.string('x86', '')),
                builder.and_(
                    builder.equal(builder.method('cpu_family', HOST_MACHINE),
                                  builder.string('x86_64', '')),
                    builder.equal(builder.method('cpu_family', HOST_MACHINE),
                                  builder.string('aarch64', ''))))),
        ]
        for data, expected in cases:
            with self.subTest():
                value = cfg.ir_to_meson(cfg.parse(iter(cfg.lexer(data)), ''))
                self.assertEqual(value, expected)
