project('cmake_code_gen', ['c', 'cpp'])

cm = import('cmake')

# Subproject with the "code generator"
sub_pro = cm.subproject('cmCodeGen')
sub_exe = sub_pro.target('genA')

# Generate the source
generated = custom_target(
  'cmake-generated',
  input: [],
  output: ['test.cpp'],
  command: [sub_exe, '@OUTPUT@']
)

# Build the exe
exe1 = executable('main1', ['main.cpp', generated])

test('test1', exe1)
