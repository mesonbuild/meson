project('man install', 'c')
m1 = install_man('foo.1')
m2 = install_man('bar.2')
install_man('vanishing/vanishing.2')
subdir('vanishing')

cdata = configuration_data()
cdata.set('TODAY', '$this_day')
b1 = configure_file(input : 'baz.1.in',
  output : 'baz.1',
  configuration : cdata)

install_man(b1)

cp = files('copy.py')
py3 = import('python').find_installation()
copy = custom_target(
  'copy',
  input : 'foo.1',
  output : 'foo_copy.1',
  command : [py3, cp, '@INPUT@', '@OUTPUT@'],
)
install_man(copy)

copy2 = custom_target(
  'copy2',
  input : 'bar.2',
  output : ['bar_copy.2', 'bar_copy.3'],
  command : [py3, cp, '@INPUT@', '@OUTPUT@'],
)
install_man(copy2)
