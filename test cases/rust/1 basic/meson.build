project('rustprog', 'rust')

e = executable('program', 'prog.rs',
  rust_args : ['-C', 'lto'], # Just a test
  install : true
)
test('rusttest', e)

subdir('subdir')
