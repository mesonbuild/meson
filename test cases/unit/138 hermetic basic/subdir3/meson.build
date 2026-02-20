py = find_program('python3')
cp = find_program('cp')

custom_target('gen-hdr',
  output: 'generated.h',
  command: [py, files('script.py'), '@OUTPUT@'],
  install: true,
  install_dir: 'include'
)

custom_target('copy-script',
  output: 'script_copy.py',
  command: [cp, files('script.py'), '@OUTPUT@'],
  install: true,
  install_dir: 'share'
)
