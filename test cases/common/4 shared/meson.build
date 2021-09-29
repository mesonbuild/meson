project('shared library test', 'c')
lib = shared_library('mylib', 'libfile.c')
build_target('mylib2', 'libfile.c', target_type: 'shared_library')

has_not_changed = false
if is_disabler(lib)
    has_not_changed = true
else
    has_not_changed = true
endif
assert(has_not_changed, 'Shared library has changed.')

assert(not is_disabler(lib), 'Shared library is a disabler.')
