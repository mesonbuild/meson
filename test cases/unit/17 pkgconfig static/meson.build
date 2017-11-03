project('pkg-config static', 'c')

if build_machine.system() != 'windows'
  prefix = meson.source_root()
else
  # pkg-config files should not use paths with \
  prefix_parts = meson.source_root().split('\\')
  prefix = '/'.join(prefix_parts)
endif

# Escape spaces
prefix_parts = prefix.split(' ')
prefix = '\ '.join(prefix_parts)

conf = configuration_data()
conf.set('PREFIX', prefix)
configure_file(input : 'foo.pc.in',
               output : 'foo.pc',
               configuration : conf)

foo_dep = dependency('foo', static : true)

test('footest', executable('foomain', 'main.c', dependencies : foo_dep))
