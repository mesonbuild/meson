project('pkgconfig consistency')

# dep1.pc has `Requires: hidden-dep1`. Since it is indirectly used from pkg-config
# we cannot override it any more.
d = dependency('dep1')
assert(d.found())
if get_option('fail1')
  meson.override_dependency('hidden-dep1', declare_dependency())
endif

# dep2.pc has `Requires: hidden-dep2`. Since we override it, dep2 cannot be used
# from pkg-config.
meson.override_dependency('hidden-dep2', declare_dependency())
d = dependency('dep2', required: false)
assert(not d.found())

# dep2 cannot be used from pkg-config, but it can still fallback to subproject.
d = dependency('dep2')
assert(d.found())
assert(d.type_name() == 'internal')
