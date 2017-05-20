project('D has arguments test', 'd')

compiler = meson.get_compiler('d')

if not compiler.compiles('int i;')
  error(''.join(['compiles is broken for d compiler: ', compiler.get_id()]))
endif
if not compiler.has_multi_arguments(['-I.', '-J.'])
  error(''.join(['has_multi_arguments is broken for d compiler: ', compiler.get_id()]))
endif
if not compiler.has_argument('-I.')
  error(''.join(['has_argument is broken for d compiler: ', compiler.get_id()]))
endif
if compiler.has_argument('-flag_a_d_compiler_defenaitly_does_not_have')
  error(''.join(['has_argument is broken for d compiler: ', compiler.get_id()]))
endif
