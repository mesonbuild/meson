project('link_early_args linking test', ['c', 'cpp'])

message('host_machine ' + host_machine.system() + ' build_machine ' + build_machine.system())

if host_machine.system() == 'linux'
  c_link_early_args = '-Wl,--defsym=func_sym=func'
  cpp_link_early_args = '-Wl,--defsym=_Z11cppfunc_symv=_Z7cppfuncv'
else
  message('unsupported on ' + host_machine.system())
  c_link_early_args = ''
  cpp_link_early_args = ''
endif

if c_link_early_args != ''
  lib = static_library('mylib', 'libfile.c', install : false)
  exe = executable('prog', 'main.c',
                   link_early_args : c_link_early_args,
                   link_with : lib)

  test('runtest', exe)

  cpplib = static_library('mycpplib', 'cpplib.cpp')
  cppexe = executable('cppprog', 'cppmain.cpp',
                      link_early_args : cpp_link_early_args,
                      link_with : cpplib)
  test('cpptest', cppexe)
endif
