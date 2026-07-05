project('test')

subproject('sub')
sometool = find_program('sometool')

custom_target('something1',
  output: 'something1',
  input: [sometool],
  command: [find_program('customtarget.py'), '@INPUT@', '@OUTPUT@'],
  build_by_default: true)

custom_target('something2',
  output: 'something2',
  input: files('foo.py'),
  command: [find_program('customtarget.py'), '@INPUT@', '@OUTPUT@'],
  depends: sometool,
  build_by_default: true)

custom_target('something3',
  output: 'something3',
  input: files('foo.py'),
  command: [find_program('customtarget.py'), '@INPUT@', '@OUTPUT@'],
  depends: find_program('foo.py'),
  build_by_default: true)

custom_target('something4',
  output: 'something4',
  input: [find_program('foo.py')],
  command: [find_program('customtarget.py'), '@INPUT@', '@OUTPUT@'],
  build_by_default: true)

test('mytest1',
  find_program('test.py'),
  args: [find_program('foo.py')],
  depends: [sometool])

test('mytest2',
  find_program('test.py'),
  args: [sometool],
  depends: [find_program('foo.py')])
