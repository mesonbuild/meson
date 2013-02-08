project('mixed C and C++', 'c', 'cxx')
exe = executable('prog', 'main.cc', 'func.c')
add_test('mixtest', exe)
