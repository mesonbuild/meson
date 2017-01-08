project('python sample', 'c')

py3_mod = import('python3')
py3 = py3_mod.find_python()

main = files('prog.py')

test('toplevel', py3, args : main)

subdir('subdir')
