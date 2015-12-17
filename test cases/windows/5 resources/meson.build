project('winmain', 'c')

win = import('windows')

exe = executable('prog', 'prog.c',
  win.compile_resources('myres.rc'),
  gui_app : true)

test('winmain', exe)
