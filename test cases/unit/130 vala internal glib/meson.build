project('vala internal glib')

if not add_languages('vala', required: false)
  error('MESON_SKIP_TEST valac not installed')
endif

glib_ver = get_option('glib-version')
if glib_ver == 'unset'
  error('Required to set -Dglib-version')
endif

glib_dep = declare_dependency(version: glib_ver)
meson.override_dependency('glib-2.0', glib_dep)

named_glib_dep = dependency('glib-2.0')

assert(named_glib_dep.type_name() == 'internal')
assert(glib_dep == named_glib_dep)

tgt = static_library('vala-tgt', 'lib.vala',
  dependencies: named_glib_dep)
