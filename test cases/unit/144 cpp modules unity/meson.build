project('cpp modules unity', 'cpp', default_options: {'cpp_std': 'c++latest'})

# Module interface units are never part of a unity file, all three sources
# would otherwise end up in the same one.
lib = static_library('lib', 'a.cpp', 'mod.ixx', 'b.cpp', override_options: {'unity': 'on'})

exe = executable('prog', 'main.cpp', objects: lib.extract_all_objects(recursive: false))
test('prog', exe)
