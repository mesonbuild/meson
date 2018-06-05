project('built library', 'c')

cc = meson.get_compiler('c')
foo_system_dep = cc.find_library('foo_in_system')
faa_pkg_dep = dependency('faa_pkg')

l = shared_library('bar_built', 'bar.c',
                   dependencies : [foo_system_dep, faa_pkg_dep])

e = executable('prog', 'prog.c', link_with: l)
test('testprog', e)
