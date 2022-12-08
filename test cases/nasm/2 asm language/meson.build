project('test', 'c')

if host_machine.cpu_family() == 'x86' and host_machine.system() == 'windows'
  asm_format = 'win32'
elif host_machine.cpu_family() == 'x86_64' and host_machine.system() == 'windows'
  asm_format = 'win64'
elif host_machine.cpu_family() == 'x86' and host_machine.system() == 'linux'
  asm_format = 'elf32'
elif host_machine.cpu_family() == 'x86_64' and host_machine.system() == 'linux'
  asm_format = 'elf64'
else
  error('MESON_SKIP_TEST: skipping test on this platform')
endif

if meson.backend().startswith('vs')
  error('MESON_SKIP_TEST: VS backend does not recognise NASM yet')
endif

if not add_languages('nasm', required: false)
  nasm = find_program('nasm', 'yasm', required: false)
  assert(not nasm.found())
  error('MESON_SKIP_TEST: nasm not found')
endif

nasm = meson.get_compiler('nasm')

code = '''
SECTION .text
global main
main:
  mov foo,bar ; error: symbol `foo' not defined
'''
assert(not nasm.compiles(code, name: 'Invalid NASM code'))

code = '''
SECTION .text
global main
main:
  mov eax,1
'''
assert(nasm.compiles(code, name: 'Valid NASM code'))

config_file = configure_file(
  output: 'config.asm',
  configuration: {'HELLO': 0},
  output_format: 'nasm',
)

cc = meson.get_compiler('c')
link_args = cc.get_supported_link_arguments(['-no-pie'])

if host_machine.system() == 'windows'
  sources = files('hello_win.asm')
else
  sources = files('hello.asm')
endif

exe = executable('hello', sources,
  nasm_args: '-DFOO',
  link_args: link_args,
)
test('hello', exe)

#Test whether pthread dependency gets filtered out
threads = dependency('threads')

exe2 = executable('hello_w_threads', 'hello.asm',
  config_file,
  nasm_args: '-DFOO',
  link_args: link_args,
  dependencies: [threads]
)

test('hello_w_threads', exe2)
