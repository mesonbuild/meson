project('pdb collisions', 'c')

executable(
  'foobar',
  'prog.c',
  install: true,
  link_with: library(
    'foobar',
    'lib.c',
    install: true,
    vs_module_defs: 'foobar.def',
  ),
)
