project('wayland-test-server', 'c')

wl_protocols_dep = dependency('wayland-protocols', required : false)
if not wl_protocols_dep.found()
  error('MESON_SKIP_TEST: wayland-protocols not installed')
endif

wl_dep = dependency('wayland-server')
wl_mod = import('unstable-wayland')

xdg_shell_xml = wl_mod.find_protocol('xdg-shell')
xdg_shell = wl_mod.scan_xml(xdg_shell_xml, side : 'server')

exe = executable('server', 'main.c', xdg_shell, dependencies : wl_dep)

test('client', exe)
