# https://github.com/mesonbuild/meson/issues/13717

project('foo', 'c')

bar_subproj = subproject('bar')
bar_dep = bar_subproj.get_variable('bar_dep', disabler())

if is_disabler(bar_dep)
    error('bar_dep is a disabler')
endif

