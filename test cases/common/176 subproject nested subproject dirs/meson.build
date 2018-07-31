project('gamma project', 'c', subproject_dir: 'contrib/subprojects')

a = subproject('alpha')
lib = a.get_variable('l')

exe = executable('prog', 'prog.c', link_with : lib)
test('basic', exe)
