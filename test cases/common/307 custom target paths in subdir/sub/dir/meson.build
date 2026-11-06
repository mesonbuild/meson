built_file = configure_file(
  output: 'built.txt',
  configuration: {'VALUE': 'built'},
)

custom_target(
  'check_paths',
  command: [
    python, files('check_paths.py'),
    '--source-root', '@SOURCE_ROOT@',
    '--build-root', '@BUILD_ROOT@',
    '--current-source-dir', '@CURRENT_SOURCE_DIR@',
    '--private-dir', '@PRIVATE_DIR@',
    '--source-file', files('input.txt'),
    '--built-file', built_file,
    '--custom-target-arg', gen_txt,
    '--input', '@INPUT@',
    '--output', '@OUTPUT@',
  ],
  input: ['input.txt', gen_txt],
  output: 'check_paths.txt',
  depend_files: files('depend.txt'),
  build_by_default: true,
)

captured = custom_target(
  'capture_feed',
  input: 'input.txt',
  command: [python, '-c', 'import sys; sys.stdout.write(sys.stdin.read())'],
  feed: true,
  capture: true,
  output: 'captured.txt',
  build_by_default: true,
)

custom_target(
  'check_capture',
  input: ['input.txt', captured],
  command: [python, files('compare.py'), '@INPUT0@', '@INPUT1@', '@OUTPUT@'],
  output: 'check_capture.txt',
  build_by_default: true,
)
