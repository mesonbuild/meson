gen = find_program('manygen.py')

buildtype = get_option('buildtype')
buildtype_args = '-Dfooxxx' # a useless compiler argument
if meson.get_compiler('c').get_id() == 'msvc'
  # We need our manually generated code to use the same CRT as the executable.
  # Taken from compilers.py since build files do not have access to this.
  if buildtype == 'debug'
    buildtype_args = '/MDd'
  elif buildtype == 'debugoptimized'
    buildtype_args = '/MDd'
  elif buildtype == 'release'
    buildtype_args = '/MD'
  endif
  outfiles = ['gen_func.lib', 'gen_func.c', 'gen_func.h', 'gen_func.o']
else
  outfiles = ['gen_func.a', 'gen_func.c', 'gen_func.h', 'gen_func.o']
endif

generated = custom_target('manygen',
  output : outfiles,
  input : ['funcinfo.def'],
  command : [gen, '@INPUT@', '@OUTDIR@', buildtype_args],
)
