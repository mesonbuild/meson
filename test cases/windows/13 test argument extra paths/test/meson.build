python3 = find_program('python3')

test('run_exe', python3, args: [files('test_run_exe.py')[0], barexe])

stamp = custom_target('stamp',
  output: 'stamp.txt',
  command: [python3, '-c', 'open("@OUTPUT@", "w").close()'],
  build_by_default: true,
)

test('run_exe_with_custom_depends', python3,
  args: [files('test_run_exe.py')[0], barexe],
  depends: stamp)
