project('dynamic_fortran', 'fortran')

dynamic = shared_library('dynamic', 'dynamic.f95')
executable('test_exe', 'main.f95', link_with : dynamic)
