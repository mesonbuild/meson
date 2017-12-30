# Should run, even though main.cpp does not exist and we call error in the last line.
# skip_rest jumps to end, so both lines are not executed.

project('example exit', 'cpp')

skip_rest()

executable('main', 'main.cpp')
error('Unreachable')

