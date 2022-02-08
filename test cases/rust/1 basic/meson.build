project('rustprog', 'rust')

e = executable('rust-program', 'prog.rs',
  rust_args : ['-C', 'lto'], # Just a test
  install : true
)
test('rusttest', e)

subdir('subdir')
