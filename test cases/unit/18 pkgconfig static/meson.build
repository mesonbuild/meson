project('pkg-config static', 'c')

# Should static link both libfoo and libbar, print warning because static
# libshared cannot be found
foo_dep = dependency('foo', static : true)
test('footest', executable('foomain', 'main.c', dependencies : foo_dep),
  args : ['foo', 'bar'])

# Should static link both libfoo and libbar, not printing warnings
foo_dep = dependency('foo', static : ['*libbar*', '*/libfoo.a'])
exe = executable('foomain-pattern1', 'main.c', dependencies : foo_dep)
test('footest-pattern1', exe, args : ['foo', 'bar'])

# Should static link only libfoo
foo_dep = dependency('foo', static : '*/libfoo.a')
exe = executable('foomain-pattern2', 'main.c', dependencies : foo_dep)
test('footest-pattern2', exe, args : ['foo'])

# Shouldn't static link anything
foo_dep = dependency('foo', static : '')
exe = executable('foomain-pattern3', 'main.c', dependencies : foo_dep)
test('footest-pattern3', exe, args : [])

# Shouldn't static link anything
foo_dep = dependency('foo', static : [])
exe = executable('foomain-pattern4', 'main.c', dependencies : foo_dep)
test('footest-pattern4', exe, args : [])
