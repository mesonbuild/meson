project('wayland-test-local', 'c')

wl_dep = dependency('wayland-client')
wl_mod = import('unstable-wayland')

xmls = files('test.xml')
gen = wl_mod.scan_xml(xmls)

exe = executable('local', 'main.c', gen, dependencies : wl_dep)

test('local', exe)
