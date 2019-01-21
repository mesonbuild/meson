project('try-static-library', 'fortran', default_options : ['default_library=static'])

static_hello = library('static_hello', 'static_hello.f90')

exe = executable('test_exe', 'main.f90', link_with : static_hello)
test('static-fortran', exe)
