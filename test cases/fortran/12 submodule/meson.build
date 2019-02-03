project('submodule single level', 'fortran')

hier2 = executable('single', 'parent.f90','child.f90')
test('single-level hierarchy', hier2)

hierN = executable('multi', 'a1.f90', 'a2.f90', 'a3.f90')
test('multi-level hierarchy', hierN)
