project('has header', 'c')

cc = meson.get_compiler('c')

if cc.has_header('stdio.h') == false
  error('Stdio missing.')
endif

if cc.has_header('ouagadougou.h')
  error('Found non-existant header.')
endif
