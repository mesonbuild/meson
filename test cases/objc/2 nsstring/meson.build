project('nsstring', 'objc')

if host_machine.system() == 'darwin'
  dep = dependency('appleframeworks', modules : 'foundation')
else
  dep = dependency('gnustep')
endif
exe = executable('stringprog', 'stringprog.m', dependencies : dep)
test('stringtest', exe)
