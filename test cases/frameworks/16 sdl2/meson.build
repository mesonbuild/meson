project('sdl2 test', 'c')

sdl2_dep = dependency('sdl2', version : '>=2.0.0', required: false)

if not sdl2_dep.found()
  error('MESON_SKIP_TEST sdl2 not found.')
endif

e = executable('sdl2prog', 'sdl2prog.c', dependencies : sdl2_dep)

test('sdl2test', e)

# Ensure that we can find it with sdl2-config too, using the legacy method name
configdep = dependency('sdl2', method : 'sdlconfig')

# And the modern method name
configdep = dependency('sdl2', method : 'config-tool')
