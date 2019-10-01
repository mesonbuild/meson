project(
  'cross test passed',
  'c',
  version : '>= 0.51'
)

e = executable('exec', 'src/main.c')

py = import('python').find_installation()

test('root', e)
test('main', py, args : [meson.current_source_dir() / 'script.py', e])
