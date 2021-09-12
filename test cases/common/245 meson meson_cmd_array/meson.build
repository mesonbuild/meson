project('check_meson_cmd_array', 'c',
  version : '0.1',
  default_options : ['warning_level=3'])

a = meson.meson_cmd_array()
res = run_command(a, '--version', check: true)
assert(res.stdout().strip() == '@0@'.format(meson.version()))
