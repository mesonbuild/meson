project('winmain', 'c')

subdir('inc')
subdir('res')

exe = executable('prog', 'prog.c',
  res,
  gui_app : true)

test('winmain', exe)
