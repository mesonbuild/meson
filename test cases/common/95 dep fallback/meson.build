project('dep fallback', 'c')

bob = dependency('boblib', fallback : ['boblib', 'bob_dep'])

exe = executable('bobtester', 'tester.c', dependencies : bob)
test('bobtester', exe)
