project('sdl2 test', 'c')

sdl2_dep = dependency('sdl2', version : '>=2.0.0', required : false)

if sdl2_dep.found()
  e = executable('sdl2prog', 'sdl2prog.c', dependencies : sdl2_dep)

  test('sdl2test', e)
endif
