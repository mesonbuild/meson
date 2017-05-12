project('mixed dependence', 'vala', 'c')

deps = [dependency('glib-2.0'), dependency('gobject-2.0')]

mixer = static_library('mixer', 'mixer.vala', 'mixer-glue.c',
  dependencies : deps)

app = executable('app', 'app.vala',
  link_with : mixer,
  dependencies : deps)

test('valamixeddependencetest', app)
