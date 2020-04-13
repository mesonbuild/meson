project('freedesktop module', 'c', license : 'MIT')

if ['darwin', 'windows', 'cygwin'].contains(host_machine.system())
  error('MESON_SKIP_TEST freedesktop module isn\'t relavent for this platform.')
endif

fdo = import('freedesktop')

exe = executable('foo', 'foo.c', install : true)

exe_desktop = fdo.desktop_file(
  exe,
  name : 'customized',
  generic_name : 'test program',
  arguments : ['--argument=$', '%F'],
  categories : ['Utility'],
  install_name : 'com.example.foo',
  icon : 'an.icon',
  mimetype : ['image/tiff', 'image/png'],
  dbus : true,
  no_display : false,
  startup_notify : true,
  startup_wm_class : 'something',
  # the validator mistakenly flags this as invalid:
  # https://gitlab.freedesktop.org/xdg/desktop-file-utils/-/issues/55
  # implements : ['test'],
  keywords : ['a keyword'],
  actions : [
    {
      'action' : 'Other',
      'exec' : ['--flag'],
      'name' : 'Something else!',
      'icon' : '/a/different/icon',
    }
  ],
  test_target : true,
)

exe_desktop_all_default = fdo.desktop_file(exe, test_target : true)
fdo.desktop_file(disabler(), test_target : true)

appstream = fdo.appstream(
  'com.example',
  'foo',
  summary : 'A foo',
  description : '<p>A very foo program. This line needs to be fairly long, even longer than you expect.</p>',
  desktop_file : exe_desktop,
  test_target : true,
)
