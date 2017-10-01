project('dolphin option', 'c')

x264_dep = dependency('x264', options : ['video', 'patented'])

exe = executable('encprog', 'encprog.c',
  dependencies : x264_dep)
test('enc test', exe)

gs = custom_target('somec',
  input : 'proggie.c.in',
  output : 'proggie.c',
  command : [exe, '@INPUT@', '@OUTPUT@'],
  )

test('Generated test', executable('proggie', gs))
