project('selinux test', 'c', meson_version: '>=1.9.0')

selinux = import('selinux')

if not selinux.found()
  error('SELinux development tools not found')
endif

pp = selinux.package('my_policy')

selinux.package('noinst_policy',
  te_file: 'no_inst.te',
  install: false
)
