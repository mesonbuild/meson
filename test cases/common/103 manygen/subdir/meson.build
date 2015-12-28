gen = find_program('manygen.py')

if meson.get_compiler('c').get_id() == 'msvc'
  outfiles = ['gen_func.lib', 'gen_func.c', 'gen_func.h', 'gen_func.o']
else
  outfiles = ['gen_func.a', 'gen_func.c', 'gen_func.h', 'gen_func.o']
endif

generated = custom_target('manygen',
  output : outfiles,
  input : ['funcinfo.def'],
  command : [gen, '@INPUT@', '@OUTDIR@'],
)
