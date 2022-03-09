project('test', 'c')

nasm = find_program('nasm', required: false)
yasm = find_program('yasm', required: false)
if not nasm.found() and not yasm.found()
  assert(not add_languages('nasm', required: false))
  error('MESON_SKIP_TEST: nasm not available')
endif

if not host_machine.cpu_family().startswith('x86')
  assert(not add_languages('nasm', required: false))
  error('MESON_SKIP_TEST: nasm only supported for x86 and x86_64')
endif

add_languages('nasm')

config_file = configure_file(
  output: 'config.asm',
  configuration: {'HELLO': 0},
  output_format: 'nasm',
)

exe = executable('hello', 'hello.asm',
  nasm_args: '-DFOO',
)
test('hello', exe)
