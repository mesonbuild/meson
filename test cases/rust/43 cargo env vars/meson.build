project('cargo env vars', 'c')

envcheck_dep = dependency('envcheck-1')
exe = executable('app', 'main.c', dependencies: envcheck_dep)
test('cargo env vars', exe)
