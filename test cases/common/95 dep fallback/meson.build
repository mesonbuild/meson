project('dep fallback', 'c')

bob = dependency('boblib', fallback : ['boblib', 'bob_dep'], required: false)
if not bob.found()
    error('Bob is actually needed')
endif
jimmy = dependency('jimmylib', fallback : ['jimmylib', 'jimmy_dep'], required: false)

exe = executable('bobtester', 'tester.c', dependencies : bob)
test('bobtester', exe)
