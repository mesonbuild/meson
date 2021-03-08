project('msvc_debuginfo', ['c', 'cpp'])

add_project_arguments('/Z7', language : 'cpp')
add_project_arguments('/ZI', language : 'c')

exe_c = executable('exe_c', 'main.c')
exe_cpp = executable('exe_cpp', 'main.cpp')

test('debuginfo_c', exe_c)
test('debuginfo_cpp', exe_cpp)
