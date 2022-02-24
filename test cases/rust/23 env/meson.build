project('rust environment variables', 'rust')

gen = find_program('generator.py')

ct = custom_target(
  'generated.rs',
  output : 'generated.rs',
  command : [gen, '@OUTDIR@'],
)

exe = executable('main', 'main.rs', ct, env: {'OUT_DIR': meson.current_build_dir()})

test('main test', exe)

# test that generated and non-generated work together
executable('static', 'static.rs')
