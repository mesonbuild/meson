project('sdl2 test', 'c')

sdl2_dep = dependency('sdl2', version : '>=2.0.0')

e = executable('sdl2prog', 'sdl2prog.c', dependencies : sdl2_dep)

test('sdl2test', e)

# Ensure that we can find it with sdl2-config too
configdep = dependency('sdl2', method : 'sdlconfig')
