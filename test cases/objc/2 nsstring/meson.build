project('nsstring', 'objc')

if host.name() == 'darwin'
  dep = find_dep('appleframeworks', modules : 'foundation', required : true)
else
  dep = find_dep('gnustep', required : true)
endif
exe = executable('stringprog', 'stringprog.m', deps : dep)
add_test('stringtest', exe)
