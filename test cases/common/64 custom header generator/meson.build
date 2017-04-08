project('custom header generator', 'c')

gen = find_program('makeheader.py')

generated_h = custom_target('makeheader.py',
output : 'myheader.lh', # Suffix not .h to ensure this works with custom suffixes, too.
input : 'input.def',
command : [gen, '@INPUT0@', '@OUTPUT0@', files('somefile.txt')])

prog = executable('prog', 'prog.c', generated_h)
test('gentest', prog)
