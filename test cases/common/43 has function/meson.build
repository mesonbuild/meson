project('has function', 'c')

cc = meson.get_compiler('c')

if not cc.has_function('printf', prefix : '#include<stdio.h>')
  error('Existing function not found.')
endif

if cc.has_function('hfkerhisadf', prefix : '#include<stdio.h>')
  error('Found non-existant function.')
endif
