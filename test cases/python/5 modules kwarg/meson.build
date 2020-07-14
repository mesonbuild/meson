project('python kwarg')

py = import('python')
prog_python = py.find_installation('python3', modules : ['distutils'])
assert(prog_python.found() == true, 'python not found when should be')
prog_python = py.find_installation('python3', modules : ['thisbetternotexistmod'], required : false)
assert(prog_python.found() == false, 'python not found but reported as found')
