project('find program', 'c')

# Test that we can find native windows executables
find_program('cmd')
find_program('cmd.exe')

# Test that a script file with an extension can be found
ext = find_program('test-script-ext.py')
test('ext', ext)
# Test that a script file without an extension can be found
prog = find_program('test-script')
test('script', prog)

dir = meson.current_source_dir() / 'not_in_path'
# Test that we can find python from path
real_python = find_program('Python')
assert(real_python.found(), 'Program should be found')
assert(not real_python.path().startswith(dir), 'Program should be from the good directory')
# Test that we can find python from search directories even if findable in path
fake_python = find_program('Python', dirs: dir)
assert(fake_python.found(), 'Program should be found')
assert(fake_python.path().startswith(dir), 'Program should be from the good directory')
