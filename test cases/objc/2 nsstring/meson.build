project('nsstring', 'objc')

if host_machine.system() == 'darwin'
  dep = dependency('appleframeworks', modules : 'foundation')
else
  dep = dependency('gnustep')
  if host_machine.system() == 'linux' and meson.get_compiler('objc').get_id() == 'clang'
    error('MESON_SKIP_TEST: GNUstep is broken on Linux with Clang')
  endif
endif
exe = executable('stringprog', 'stringprog.m', dependencies : dep)
test('stringtest', exe)
