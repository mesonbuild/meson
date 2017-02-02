project('generated assembly', 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  error('MESON_SKIP_TEST: assembly files cannot be compiled directly by MSVC')
endif

cpu = host_machine.cpu_family()
supported_cpus = ['arm', 'x86', 'x86_64']

if not supported_cpus.contains(cpu)
  error('MESON_SKIP_TEST: unsupported cpu family: ' + cpu)
endif

if cc.symbols_have_underscore_prefix()
  add_project_arguments('-DMESON_TEST__UNDERSCORE_SYMBOL', language : 'c')
endif

copy = find_program('copyfile.py')
output = 'square-@0@.S'.format(cpu)
input = output + '.in'

copygen = generator(copy,
  arguments : ['@INPUT@', '@OUTPUT@'],
  output : '@BASENAME@')

l = shared_library('square-gen', copygen.process(input))

test('square-gen-test', executable('square-gen-test', 'main.c', link_with : l))

copyct = custom_target('square',
  input : input,
  output : output,
  command : [copy, '@INPUT@', '@OUTPUT@'])

l = shared_library('square-ct', copyct)

test('square-ct-test', executable('square-ct-test', 'main.c', link_with : l))
