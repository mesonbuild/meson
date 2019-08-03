# Generate an executable manually.
e = custom_target('prog',
  input : ['prog.c', objlib.extract_objects('source.c')],
  output : outputname,
  command : [comp, cc, '@OUTPUT@', '@INPUT@'])
