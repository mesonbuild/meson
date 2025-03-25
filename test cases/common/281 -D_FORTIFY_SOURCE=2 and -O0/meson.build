project('check header', 'c', 'cpp', default_options: ['werror=true'])

fallback = ''

if not meson.get_compiler('c').has_argument('-Werror', required: false)
  error('MESON_SKIP_TEST: -Werror is not available')
endif

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  assert(comp.check_header('stdio.h', prefix : fallback, args: '-Werror'), 'Stdio missing.')
endforeach
