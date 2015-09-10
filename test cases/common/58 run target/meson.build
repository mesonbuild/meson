project('run target', 'c')

run_target('mycommand', 'scripts/script.sh')

# Make it possible to run built programs.
# In cross builds exe_wrapper should be added if it exists.

exe = executable('helloprinter', 'helloprinter.c')
run_target('runhello', exe, 'argument')
