project('underspecified deps', 'c')

runner = find_program('runner.py')
exe1 = executable('main1', 'main.c')
exe2 = executable('main2', 'main.c')

test('runner-with-exedep', runner, args: exe1)
test('runner-without-dep', runner, args: exe2.full_path())
