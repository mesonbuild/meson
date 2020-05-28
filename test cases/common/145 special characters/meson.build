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

# test that we can pass these special characters in compiler arguments
#
# (this part of the test is crafted so we don't try to use these special
# characters in filenames or target names)
#
# TODO: similar tests needed for languages other than C
# TODO: add similar test for quote and doublequote, carefully

special = [
  ['amp', '&'],
  ['at', '@'],
  ['backslash', '\\'],
  ['dollar', '$'],
  ['gt', '>'],
  ['hash', '#'],
  ['lt', '<'],
  ['slash', '/'],
]

# set to true if you want the builder to go green, false to see the bugs in action
skipbugs = true
cc = meson.get_compiler('c')

foreach s : special
  if skipbugs and (s[0] == 'hash') and (cc.get_id() == 'msvc')
    message('passing the hash char fails always at runtime with msvc (CHAR is "="?!, arg is ok)')
  else
    args = '-DCHAR="@0@"'.format(s[1])
    e = executable('arg-string-' + s[0], 'arg-string-test.c', c_args: args)
    test('arg-string-' + s[0], e, args: s[1])
  endif

  if skipbugs and (s[0] == 'hash') and (cc.get_id() == 'msvc')
    message('passing the hash char fails always at runtime with msvc (CHAR is "="?!, arg is ok)')
  else
    args = '-DCHAR=@0@'.format(s[1])
    e = executable('arg-unquoted-' + s[0], 'arg-unquoted-test.c', c_args: args)
    test('arg-unquoted-' + s[0], e, args: s[1])
  endif
endforeach

foreach s : special
  if skipbugs and (s[0] == 'hash') and (cc.get_id() == 'msvc')
    message('passing the hash char fails always at runtime with msvc (CHAR is "="?!, arg is ok)')
  else
    args = '-DCHAR=\'@0@\''.format(s[1])
    e = executable('arg-char-' + s[0], 'arg-char-test.c', c_args: args)
    test('arg-char-' + s[0], e, args: s[1])
  endif
endforeach
