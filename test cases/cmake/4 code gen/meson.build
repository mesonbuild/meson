project('cmake_code_gen', ['c', 'cpp'])

# Subproject with the "code generator"
sub_pro = subproject('cmCodeGen')
sub_exe = sub_pro.get_variable('genA')

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
