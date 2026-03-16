project('rustprog', 'rust', default_options : ['b_ndebug=true'])

e = executable('rust-program', 'prog.rs',
  install : true
)
test('rusttest', e)
