project('dynamic_fortran', 'fortran', default_options : ['default_library=shared'])

dynamic = library('dynamic', 'dynamic.f90')
exe = executable('test_exe', 'main.f90', link_with : dynamic)
test('dynamic-fortran', exe)
