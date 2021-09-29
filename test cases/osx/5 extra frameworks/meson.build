project('xcode extra framework test', 'c')

dep_libs = dependency('OpenGL', method : 'extraframework')
assert(dep_libs.type_name() == 'extraframeworks', 'type_name is ' + dep_libs.type_name())

dep_main = dependency('Foundation')
assert(dep_main.type_name() == 'extraframeworks', 'type_name is ' + dep_main.type_name())

dep_py = dependency('python', method : 'extraframework')
assert(dep_main.type_name() == 'extraframeworks', 'type_name is ' + dep_main.type_name())

stlib = static_library('stat', 'stat.c', install : true, dependencies: dep_libs)
exe = executable('prog', 'prog.c', install : true, dependencies: dep_main)
