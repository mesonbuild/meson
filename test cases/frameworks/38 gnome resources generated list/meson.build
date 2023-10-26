project('meson-example', 'c')

gnome = import('gnome', required: false)

if not gnome.found()
  error('MESON_SKIP_TEST: gnome module not supported')
endif

glib = dependency('glib-2.0', required: false)

if not glib.found()
  error('MESON_SKIP_TEST glib not found.')
endif

test_generator = generator(
  find_program('cat'),
  output: '@BASENAME@.gen.txt',
  capture: true,
  arguments: ['@INPUT@']
)

generated = test_generator.process(
  'test_normal.txt',
  'resources/test_nested.txt',
  preserve_path_from: meson.current_source_dir()
)

gnome.compile_resources(
  'demo',
  'test.gresource.xml',
  c_name: 'test_res',
  dependencies: generated
)

gnome.compile_resources(
  'demo-gresource',
  'test.gresource.xml',
  gresource_bundle: true,
  build_by_default: true,
  dependencies: generated
)
