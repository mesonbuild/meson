project('subfoo', 'c')

true_cmd = find_program('true.py')

bar_exe = executable('bar', 'bar.c')
alias_target('bar_alias', bar_exe)
run_target('nop', command : [true_cmd])
custom_target('cus', output: ['cus.c'], command : [true_cmd])
