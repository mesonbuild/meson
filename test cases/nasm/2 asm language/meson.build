project('test', 'c')

if not host_machine.cpu_family().startswith('x86')
  assert(not add_languages('nasm', required: false))
  error('MESON_SKIP_TEST: nasm only supported for x86 and x86_64')
endif

if not add_languages('nasm', required: false)
  nasm = find_program('nasm', 'yasm', required: false)
  assert(not nasm.found())
  error('MESON_SKIP_TEST: nasm not found')
endif

config_file = configure_file(
  output: 'config.asm',
  configuration: {'HELLO': 0},
  output_format: 'nasm',
)

exe = executable('hello', 'hello.asm',
  nasm_args: '-DFOO',
)
test('hello', exe)
