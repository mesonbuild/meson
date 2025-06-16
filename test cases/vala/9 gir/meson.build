# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Intel Corporation

project('foo', 'c', 'vala')

glib = dependency('glib-2.0')
gobject = dependency('gobject-2.0')
g_ir_compiler = find_program('g-ir-compiler')

foo = shared_library('foo', 'foo.vala',
                     install : true,
                     install_dir : [true, false, false, true],
                     vala_gir: 'Foo-1.0.gir',
                     dependencies: [glib, gobject])

custom_target('foo-typelib',
              command: [g_ir_compiler, '--output', '@OUTPUT@', '@INPUT@'],
              input: foo.vala_gir(),
              output: 'Foo-1.0.typelib',
              build_by_default : true)
