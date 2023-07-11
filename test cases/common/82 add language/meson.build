project('add language', 'c')

test('C', executable('cprog', 'prog.c'))

assert(add_languages('cpp', native: false), 'Add_languages returned false on success')
assert(not add_languages('klingon', required : false), 'Add_languages returned true on failure.')

test('C++', executable('cppprog', 'prog.cc'))

add_languages('c', native: false)

cpp = meson.get_compiler('cpp', native : false)

# We have at least one CI setup that has only cross compilers, so both will fail
if add_languages('cpp', native : true, required : false)
  assert(add_languages('cpp', native : 'both'), 'Add_languages returned false on success')
  cpp_build = meson.get_compiler('cpp', native : true)
endif
