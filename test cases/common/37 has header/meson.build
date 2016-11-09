project('has header', 'c', 'cpp')

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  if comp.has_header('stdio.h') == false
    error('Stdio missing.')
  endif

  if comp.has_header('ouagadougou.h')
    error('Found non-existant header.')
  endif
endforeach
