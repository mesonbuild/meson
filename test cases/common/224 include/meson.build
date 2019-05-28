# Should read instructions given in included_file

project('example include', 'c')

variable = 1

assert(variable == 1, 'variable doesn\'t have correct value')

include('incr_variable.meson')

assert(variable == 2, 'variable doesn\'t have correct value')

# An executable is declared in included_file
include('executable.meson')

