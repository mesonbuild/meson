project('unity extract separate sources', 'c')

# The assembly file is compiled on its own even in a unity build, the objects
# extracted from the library must match the objects that were really built.
if meson.get_compiler('c').get_argument_syntax() == 'msvc'
  add_languages('masm', native: false)
  asm = 'empty.masm'
else
  asm = 'empty.S'
endif

lib = static_library('lib', 'one.c', 'two.c', asm)

exe = executable('prog', 'prog.c', objects: lib.extract_all_objects(recursive: false))
test('prog', exe)
