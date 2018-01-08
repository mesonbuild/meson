# Should run, even though main.cpp does not exist and we call error in the last line.
# return_to_parent_dir jumps to end, so both lines are not executed.

project('example exit', 'cpp')

return_to_calling_dir()

executable('main', 'main.cpp')
error('Unreachable')

