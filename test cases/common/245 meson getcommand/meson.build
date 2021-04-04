project('check_get_command', 'c',
  version : '0.1',
  default_options : ['warning_level=3'])

a = meson.get_command()
res = run_command(a, '--version', check: true)
assert(res.stdout().strip() == '@0@'.format(meson.version()))
