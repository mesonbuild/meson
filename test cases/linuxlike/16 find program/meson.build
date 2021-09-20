project('find program', 'c')

dir = meson.current_source_dir() / 'not_in_path'

real_python = find_program('python3')
assert(real_python.found(), 'Program should be found')
assert(not real_python.path().startswith(dir), 'Program should be from the good directory')

fake_python = find_program('python3', dirs: dir)
assert(fake_python.found(), 'Program should be found')
assert(fake_python.path().startswith(dir), 'Program should be from the good directory')
