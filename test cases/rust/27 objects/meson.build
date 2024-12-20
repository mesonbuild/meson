project('staticlib group', 'c', 'rust', meson_version: '>=1.8.0')

lib1 = static_library('lib1', 'lib1.c')
dep1 = declare_dependency(objects: lib1.extract_all_objects(recursive: false))
lib2 = static_library('lib2', 'lib2.c')
dep2 = declare_dependency(objects: lib2.extract_all_objects(recursive: false))
executable('lib1objs', 'main.rs',
  objects: lib1.extract_all_objects(recursive: false),
  link_with: lib2)
executable('lib2objs', 'main.rs',
  objects: lib2.extract_all_objects(recursive: false),
  link_with: lib1)
executable('lib1objs_as_dep', 'main.rs',
  dependencies: dep1,
  link_with: lib2)
executable('lib2objs_as_dep', 'main.rs',
  dependencies: dep2,
  link_with: lib1)
