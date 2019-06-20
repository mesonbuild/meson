project('cross file name suffixes', 'c')

exe = executable('executable', ['executable.c'])
assert(exe.full_path().endswith('.exe_test'), 'exe_suffix is honored')

static_lib = static_library('static_library', ['library.c'])
assert(static_lib.full_path().endswith('.a_test'), 'static_lib_suffix is honored')

shared_lib = shared_library('shared_library', ['library.c'])
assert(shared_lib.full_path().endswith('.so_test'), 'shared_lib_suffix is honored')

shared_mod = shared_module('shared_module', ['library.c'])
assert(shared_mod.full_path().endswith('.sm_test'), 'shared_module_suffix is honored')
