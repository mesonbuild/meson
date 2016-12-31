custom_target('thing',
output : 'final.dat',
input : cfile,
command : [find_program('mycompiler.py'), '@INPUT@', '@OUTPUT@'])

# Test usage of a `configure_file` as part of the command list
py3 = find_python3()

compiler = configure_file(input : 'mycompiler.py',
  output : 'mycompiler2.py',
  configuration : configuration_data())

custom_target('thing2',
output : 'final2.dat',
input : cfile,
command : [py3, compiler, '@INPUT@', '@OUTPUT@'])
