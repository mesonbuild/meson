project('orctest', 'orc', 'C')

cc = meson.get_compiler('c')

math_dep = cc.find_library('m', required: true)
orc_dep = [dependency('orc-0.4')]

e = executable('orctest', ['prog.orc', 'main.c'], dependencies: [orc_dep, math_dep])
test('orctest', e)
