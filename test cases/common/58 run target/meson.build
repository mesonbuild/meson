project('run target', 'c')

run_target('mycommand', 'scripts/script.sh')

# Make it possible to run built programs.
# In cross builds exe_wrapper should be added if it exists.

exe = executable('helloprinter', 'helloprinter.c')
run_target('runhello', exe, 'argument')

python3 = find_program('python3')
run_target('py3hi', python3, '-c', 'print("I am Python3.")')
