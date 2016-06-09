project('has arg', 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  is_arg = '/O2'
else
  is_arg = '-O2'
endif

isnt_arg = '-fiambroken'

assert(cc.has_arg(is_arg), 'Arg that should have worked does not work.')
assert(not cc.has_arg(isnt_arg), 'Arg that should be broken is not.')
