runner = find_program('copyrunner.py')

copier = executable('copier', 'filecopier.c', native: true)

cg = generator(runner,
    output: ['@BASENAME@.c'],
    arguments: [copier.path(), '@INPUT@', '@OUTPUT@'],
    depends: copier)

test('generatordep',
    executable('gd', 'prog.c', cg.process('libsrc.c.in')))
