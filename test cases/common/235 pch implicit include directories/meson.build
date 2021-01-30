project('PCH implicit include directories', 'cpp')
# This example should have 3 steps:
# 1) PCH step
# 2) Compile step (which will require -Iprog.p)
# 3) Link step
e_pch = executable('e_pch', sources : 'main.cpp' , cpp_pch : 'pch/myexe_pch.hpp',
  implicit_include_directories : false)
test('e_pch', e_pch)

# This example should have 2 steps:
# 1) Compile step (which will not require -Iprog.p)
# 2) Link step
e_no_pch = executable('e_no_pch', sources : 'main.cpp', implicit_include_directories : false)
test('e_no_pch', e_no_pch)
