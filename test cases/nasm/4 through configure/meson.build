project('through configure')

if not add_languages('nasm', required: false)
  error('MESON_SKIP_TEST: nasm not found')
endif

if not host_machine.cpu_family().startswith('x86')
  assert(not add_languages('nasm', required: false))
  error('MESON_SKIP_TEST: nasm only supported for x86 and x86_64')
endif

if meson.backend().startswith('vs')
  error('MESON_SKIP_TEST: VS backend does not recognise NASM yet')
endif

section = host_machine.system() == 'macos' ? '.rodata' : '.rdata'  

sources = configure_file(
  input: 'dummy.asm.in',
  output: 'dummy.asm',
  configuration: {
    'section': section
  }
)

dummy = library(
    'dummy',
    sources,
    vs_module_defs: 'dummy.def',
)
