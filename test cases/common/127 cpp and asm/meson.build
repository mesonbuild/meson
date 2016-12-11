project('c++ and assembly test', 'cpp')

sources = ['trivial.cc']
# If the compiler cannot compile assembly, don't use it
if meson.get_compiler('cpp').get_id() != 'msvc'
  cpu = host_machine.cpu_family()
  sources += ['retval-' + cpu + '.S']
  cpp_args = ['-DUSE_ASM']
  message('Using ASM')
else
  cpp_args = ['-DNO_USE_ASM']
endif

exe = executable('trivialprog', sources,
  cpp_args : cpp_args)
test('runtest', exe)
