gen = find_program('manygen.py')

generated = custom_target('manygen',
  output : ['gen_func.a', 'gen_func.c', 'gen_func.h', 'gen_func.o'],
  input : ['funcinfo.def'],
  command : [gen, '@INPUT@', '@OUTDIR@'],
)
