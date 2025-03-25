project('check header', 'c', 'cpp')

fallback = ''

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  assert(comp.check_header('stdio.h', prefix : fallback), 'Stdio missing.')
endforeach
