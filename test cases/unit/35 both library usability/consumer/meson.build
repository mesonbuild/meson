project('both libraries consumer', 'c')

d1 = dependency('whole-installed')
d2 = dependency('whole-internal')
d3 = dependency('with-installed')
d4 = dependency('with-internal')

test('both-whole-installed', executable('tester1', 'tester.c', dependencies : d1))
test('both-whole-internal', executable('tester2', 'tester.c', dependencies : d2))
test('both-with-installed', executable('tester3', 'tester.c', dependencies : d3))
test('both-with-internal', executable('tester4', 'tester.c', dependencies : d4))
