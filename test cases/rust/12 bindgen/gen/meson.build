gen_h = custom_target(
  'gen.h',
  command : [find_program('gen_header.py'), '@INPUT@', '@OUTPUT@'],
  output : 'gen.h',
  input : meson.project_source_root() / 'src/header.h'
)

gen2_h = custom_target(
  'other.h',
  command : [find_program('gen_header.py'), '@INPUT@', '@OUTPUT@'],
  output : 'other.h',
  input : meson.project_source_root() / 'include/other.h'
)
