# use C++ to make it harder
project('mixed', ['cpp', 'rust'])

e1 = executable('mixed', 'hello.rs', 'main.cc')
e2 = executable('mixed-structured', structured_sources('hello.rs'), 'main.cc')

hello2 = import('fs').copyfile('hello.rs', 'hello2.rs')
e3 = executable('mixed-structured-gen', structured_sources(hello2), 'main.cc')

test('mixed', e1)
test('mixed-structured', e2)
test('mixed-structured-gen', e3)
