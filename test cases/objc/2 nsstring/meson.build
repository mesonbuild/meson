project('nsstring', 'objc')

if host.name() == 'darwin'
  dep = find_dep('appleframeworks', modules : 'foundation')
else
  dep = find_dep('gnustep')
endif
exe = executable('stringprog', 'stringprog.m', deps : dep)
test('stringtest', exe)
