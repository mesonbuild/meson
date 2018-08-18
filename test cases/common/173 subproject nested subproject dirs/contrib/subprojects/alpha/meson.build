project('alpha project', 'c', subproject_dir: 'var/subprojects')

b = subproject('beta')
l = shared_library('a', 'a.c', link_with : b.get_variable('lb'))
