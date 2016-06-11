project('has arg', 'c', 'cpp')

cc = meson.get_compiler('c')
cpp = meson.get_compiler('cpp')

if cc.get_id() == 'msvc'
  is_arg = '/O2'
  useless = '/DFOO'
else
  is_arg = '-O2'
  useless = '-DFOO'
endif

isnt_arg = '-fiambroken'

assert(cc.has_argument(is_arg), 'Arg that should have worked does not work.')
assert(not cc.has_argument(isnt_arg), 'Arg that should be broken is not.')

assert(cpp.has_argument(is_arg), 'Arg that should have worked does not work.')
assert(not cpp.has_argument(isnt_arg), 'Arg that should be broken is not.')

# Have useless at the end to ensure that the search goes from front to back.
l1 = cc.first_supported_argument([isnt_arg, is_arg, isnt_arg, useless])
l2 = cc.first_supported_argument(isnt_arg, isnt_arg, isnt_arg)

assert(l1.length() == 1, 'First supported returned wrong result.')
assert(l1.get(0) == is_arg, 'First supported returned wrong argument.')
assert(l2.length() == 0, 'First supported did not return empty array.')

l1 = cpp.first_supported_argument([isnt_arg, is_arg, isnt_arg, useless])
l2 = cpp.first_supported_argument(isnt_arg, isnt_arg, isnt_arg)

assert(l1.length() == 1, 'First supported returned wrong result.')
assert(l1.get(0) == is_arg, 'First supported returned wrong argument.')
assert(l2.length() == 0, 'First supported did not return empty array.')
