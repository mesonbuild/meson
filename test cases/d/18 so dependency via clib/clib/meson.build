# Shared library as a subproject is handled differently than a library found with pkg-config,
# let's add it to see the difference.
exampleshlib_proj = subproject('exampleshlib')
exampleshlib_dep = exampleshlib_proj.get_variable('exampleshlib_dep')

# D standard runtime library (Phobos) bundles a copy of zlib (etc.c.zlib) and exports zlib C symbols globally
# thus any reference to zlib functions get resolved via D's standard library and that prevents reproducing the bug.
# We try with libxml2 as another widely deployed library instead.
libxml2_dep = dependency('libxml-2.0')
if not libxml2_dep.found()
  error('MESON_SKIP_TEST requires libxml2')
endif

clib_lib = static_library('clib',
    'clib.c',
    dependencies : [libxml2_dep, exampleshlib_dep]
)

clib_dep = declare_dependency(
    link_with : clib_lib,
    dependencies : [libxml2_dep, exampleshlib_dep],
    include_directories : include_directories('.'),
)
