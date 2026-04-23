# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024-2025 Intel Corporation

project('flex and bison', 'c', meson_version : '>= 1.10.0')

# The point of this test is that one generator
# may output headers that are necessary to build
# the sources of a different generator.

flex = find_program('reflex', 'flex', 'lex', 'win_flex', required: false)
if not flex.found()
  error('MESON_SKIP_TEST flex not found.')
endif

bison = find_program('bison', 'byacc', 'yacc', 'win_bison', required: false)
if not bison.found()
  error('MESON_SKIP_TEST bison not found.')
endif

codegen = import('unstable-codegen')
lex = codegen.lex()
message('lex implementation:', lex.implementation())
lfiles = lex.generate('lexer.l', header: '@PLAINNAME@.h')

yacc = codegen.yacc()
message('yacc implementation:', yacc.implementation())
pfiles = yacc.generate('parser.y', header : '@BASENAME@.tab.h')

e = executable(
  'pgen',
  'prog.c', lfiles, pfiles,
  override_options : ['unity=off'],
)

test('parsertest', e,
    args: [meson.current_source_dir() / 'testfile'])
