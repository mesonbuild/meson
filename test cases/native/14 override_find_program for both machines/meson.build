project('override for both machines', 'c', meson_version : '>= 1.12.0')

subproject('tools')
subproject('tools', native : true)

tool = find_program('mytool', required: false)
if not tool.found()
  # If a tool produces machine-independent output, it can be
  # looked up with `native: true`.
  tool = find_program('mytool', native : true)
endif

ct = custom_target(
  'generated',
  command : [tool],
  output : 'generated.txt',
  capture : true,
  build_by_default : true,
)

e = executable('prog', 'prog.c')
test('prog', e)
