project('test', 'c')

mod_py = import('python')
python = mod_py.find_installation()

test_target = custom_target(
  'test_target',
  input : [files('gen.py'), files('foo')],
  output : 'bar',
  command : [python, '@INPUT0@', '@INPUT1@', '@OUTPUT@'],
  build_by_default : true,
)
