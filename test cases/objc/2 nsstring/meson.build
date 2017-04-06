project('nsstring', 'objc')

if host_machine.system() == 'darwin'
  dep = dependency('appleframeworks', modules : 'foundation')
elif host_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST GNUstep is not packaged for Cygwin.')
else
  dep = dependency('gnustep')
  if host_machine.system() == 'linux' and meson.get_compiler('objc').get_id() == 'clang'
    error('MESON_SKIP_TEST: GNUstep is broken on Linux with Clang')
  endif
endif
exe = executable('stringprog', 'stringprog.m', dependencies : dep)
test('stringtest', exe)
