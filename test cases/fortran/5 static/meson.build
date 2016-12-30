project('try-static-library', 'fortran')

static_hello = static_library('static_hello', 'static_hello.f90')

executable('test_exe', 'main.f90', link_with : static_hello)
