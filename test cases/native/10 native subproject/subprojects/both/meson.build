project('both', 'c')

cross = meson.is_cross_build() ? 1 : 0
add_project_arguments(f'-DPROJECT_CROSS_BUILD=@cross@', language : 'c')

e = executable('main', 'main.c', c_args : f'-DEXPECTED_CROSS_BUILD=@cross@')
test('main', e)
