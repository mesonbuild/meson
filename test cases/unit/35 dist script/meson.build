project('dist script', 'c',
  version : '1.0.0')

exe = executable('comparer', 'prog.c')
test('compare', exe)
distprog = executable('dist-helper', 'distprog.c')
meson.override_find_program('dist-helper', distprog)

meson.add_dist_script('replacer.py', '"incorrect"', '"correct"')
meson.add_dist_script(find_program('replacer.py'), '"incorrect"', '"correct"')
testcase expect_error('Program \'dist-helper\' was overridden with the compiled executable \'dist-helper\' and therefore cannot be used during configuration')
  meson.add_dist_script(find_program('dist-helper'))
endtestcase

subproject('sub')
