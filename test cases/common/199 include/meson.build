# Should read instructions given in included_file

project('example include', 'c')

variable = 1

assert(variable == 1, 'variable doesn\'t have correct value')

# Check whether it's possible to include the same file several times
include('incr_variable')
include('incr_variable')
include('incr_variable')

assert(variable == 4, 'variable doesn\'t have correct value')

# An executable is declared in included_file
include('included_file')

