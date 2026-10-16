project('cpp modules unity', 'cpp', default_options: {'cpp_std': 'c++latest'})

# Module interface units are never part of a unity file, all three sources
# would otherwise end up in the same one. a.cpp imports the module from inside
# the unity file.
lib = static_library('lib', 'a.cpp', 'mod.ixx', 'b.cpp', override_options: {'unity': 'on'})

exe = executable('prog', 'main.cpp', objects: lib.extract_all_objects(recursive: false))
test('prog', exe)

# Imports the module of another target from inside a unity file.
user = static_library('user', 'user.cpp', link_with: lib, override_options: {'unity': 'on'})

exe_user = executable('prog_user', 'main_user.cpp', link_with: user)
test('prog_user', exe_user)
