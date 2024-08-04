project('foo', ['objc'])

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objc is not supported by vs backend')
endif

l = static_library('foo', 'foo.m')

foo_dep = declare_dependency(link_with : l)
