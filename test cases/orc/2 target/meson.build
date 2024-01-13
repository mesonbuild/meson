project('orctest', 'orc', 'C')

cc = meson.get_compiler('c')
orcc = meson.get_compiler('orc')

math_dep = cc.find_library('m', required: true)
orc_dep = [dependency('orc-0.4')]
orc_args = ['--target', 'mmx']

e = executable('orctest', ['prog.orc', 'main.c'], dependencies: [orc_dep, math_dep], orc_args: orc_args)
test('orctest', e)
