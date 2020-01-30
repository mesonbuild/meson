project('libdir prefix', 'c',
  default_options : ['libdir=/opt/lib'])

if host_machine.system() == 'windows'
  error('MESON_SKIP_TEST: this test does not work on Windows since /foo is not absolute')
endif