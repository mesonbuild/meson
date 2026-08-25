project('sub')

custom_target('t',
  output: 'out',
  command: [find_program('touch.py'), '@OUTPUT@'],
  depend_files: '../../shared.py',
  build_by_default: true,
)
