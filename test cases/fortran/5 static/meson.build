project('try-static-library', 'fortran')

static_hello = static_library('static_hello', 'static_hello.f95')

executable('test_exe', 'main.f95', link_with : static_hello)
