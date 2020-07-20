project('disabler_inside_array', 'c')

exes = []

exes += executable('a', 'test.c')

exes += executable('b', 'test.c', dependencies : disabler())

exes += executable('c', 'test.c')
