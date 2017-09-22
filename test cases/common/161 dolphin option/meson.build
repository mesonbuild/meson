project('dolphin option', 'c')

x264_dep = dependency('x264', options : ['video', 'patented'])

exe = executable('encprog', 'encprog.c',
  dependencies : x264_dep)
test('enc test', exe)

