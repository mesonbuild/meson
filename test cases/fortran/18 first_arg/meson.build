project('fortran_args', 'fortran')

fc = meson.get_compiler('fortran')

if fc.get_id() == 'intel-cl'
  is_arg = '/O2'
  useless = '/DFOO'
else
  is_arg = '-O2'
  useless = '-DFOO'
endif

isnt_arg = '-fiambroken'

assert(fc.has_argument(is_arg), 'Arg that should have worked does not work.')
assert(not fc.has_argument(isnt_arg), 'Arg that should be broken is not.')

assert(fc.get_supported_arguments([is_arg, isnt_arg, useless]) == [is_arg, useless], 'Arg filtering returned different result.')

# Have useless at the end to ensure that the search goes from front to back.
l1 = fc.first_supported_argument([isnt_arg, is_arg, isnt_arg, useless])
l2 = fc.first_supported_argument(isnt_arg, isnt_arg, isnt_arg)

assert(l1.length() == 1, 'First supported returned wrong result.')
assert(l1.get(0) == is_arg, 'First supported returned wrong argument.')
assert(l2.length() == 0, 'First supported did not return empty array.')
