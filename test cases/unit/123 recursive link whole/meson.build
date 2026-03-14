project('testmeson', 'c',
  version : '0.1',
  default_options : [
    'warning_level=3',
    'default_library=static',
  ],
  meson_version: '>=1.6.0')

depsub = dependency('sub') # Subproject, linked statically
libshared = shared_library('shared', 'libshared.c') # Shared library, linked dynamically
libwhole = static_library('whole', 'libwhole.c') # Static library, using regular link_whole

lib1 = static_library('1', 'lib1.c', dependencies : [depsub])
dep1 = declare_dependency(link_with : [lib1, libshared], link_whole : [libwhole])

lib2 = static_library('2', 'lib2.c', dependencies : dep1)
dep2 = declare_dependency(link_with : lib2)

# It should link to lib1, lib2, libwhole and libsub statically and to libshared dynamically
lib3 = static_library('3', 'lib3.c', dependencies : dep2.as_link_whole(recursive: true))

# The executable should only link to lib3 and libshared
exe = executable('testmeson', 'main.c', link_with : lib3)

test('basic', exe)
