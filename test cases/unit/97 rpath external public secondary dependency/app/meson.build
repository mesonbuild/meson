project('app', ['c'])

libA = dependency('libA')
libB = dependency('libB')

app = executable('app', 'app.c', dependencies : [libA, libB])
test('app test', app)
