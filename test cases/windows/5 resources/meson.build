project('winmain', 'c')

win = import('windows')
res = win.compile_resources('myres.rc',
  include_directories : include_directories('inc')
)

exe = executable('prog', 'prog.c',
  res,
  gui_app : true)

test('winmain', exe)
