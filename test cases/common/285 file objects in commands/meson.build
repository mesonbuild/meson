project('file objects in commands')

# Tests fix for GitHub issue #11255
codegen = configure_file(
  input: 'codegen.py.in',
  output: 'codegen.py',
  copy: true
)

buildtool = files('buildtool.py')

custom_target('generate-code',
  output: 'generated.h',
  command: [codegen],
  capture: true,
  build_by_default: true
)

custom_target('process-data',
  output: 'processed.txt',
  command: [buildtool, 'Processing data'],
  capture: true,
  build_by_default: true
)

run_target('run-codegen',
  command: [codegen]
)
