project('install test', 'c')

stlib = static_library('stat', 'stat.c', install : true)
shlib = shared_library('shar', 'shar.c', install : true)
exe = executable('prog', 'prog.c', install : true)
