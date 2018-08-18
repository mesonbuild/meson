project('ninja special characters' ,'c')

python = import('python3').find_python()

# Without newlines, this should appear directly in build.ninja.
gen = custom_target('gen',
  command : [
    python,
    files('check_quoting.py'),
    'dollar=$',
    'colon=:',
    'space= ',
    '''multi1=  ::$$  ::$$''',
    '@OUTPUT@'],
  output : 'result',
  install : true,
  install_dir : get_option('datadir'))

# With newlines, this should go through the exe wrapper.
gen2 = custom_target('gen2',
  command : [
    python,
    files('check_quoting.py'),
    '''newline=
''',
    'dollar=$',
    'colon=:',
    'space= ',
    '''multi2=  ::$$

  

::$$''',
    '@OUTPUT@'],
  output : 'result2',
  install : true,
  install_dir : get_option('datadir'))
