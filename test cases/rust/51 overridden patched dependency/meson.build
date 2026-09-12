project('nested overridden Cargo dependency', 'rust', meson_version: '>= 1.11')

ws = import('rust').workspace()

# While processing `outer`, use the patched leaf and patched packages
subdir('leaf')
subdir('patched')
ws.subproject('outer', '1')
