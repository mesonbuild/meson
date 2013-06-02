project('nsstring', 'objc')

if host.name() == 'darwin'
  dep = dependency('appleframeworks', modules : 'foundation')
else
  dep = dependency('gnustep')
endif
exe = executable('stringprog', 'stringprog.m', deps : dep)
test('stringtest', exe)
