project('subdir if found', 'c')

not_found_dep = dependency('nonexisting', required : false)

variable = 3

include('included_file', if_found : not_found_dep)
assert(variable == 3, 'included_file was unexpectedly included.')
