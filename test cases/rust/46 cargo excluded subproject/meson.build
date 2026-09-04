project('rust excluded subproject', 'rust', meson_version: '>= 1.13')

cargo = import('rust').workspace()
if 'mylib' in cargo.packages()
    error('Excluded subproject is a workspace member')
endif

test('toplevel', cargo.package().executable())
