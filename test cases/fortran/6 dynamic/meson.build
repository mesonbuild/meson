project('dynamic_fortran', 'fortran')

dynamic = shared_library('dynamic', 'dynamic.f90')
exe = executable('test_exe', 'main.f90', link_with : dynamic)
test('dynamic-fortran', exe)
