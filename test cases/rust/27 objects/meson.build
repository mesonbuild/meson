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

lib12 = shared_library('dylib2objs', 'lib1-dylib.rs',
  objects: lib2.extract_all_objects(recursive: false),
  rust_abi: 'c')
executable('dylib', 'main.rs', link_with: lib12)

lib12 = shared_library('dylib2objs_as_dep', 'lib1-dylib.rs',
  dependencies: dep2,
  rust_abi: 'c')
executable('dylib_as_dep', 'main.rs', link_with: lib12)
