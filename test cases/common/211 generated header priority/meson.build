project('subproj_indirect_include', 'c')

subproj = subproject('subproj_with_config_header')
subproj_dep = subproj.get_variable('subproj_dep')

exe = executable('exe', 'main.c', dependencies : subproj_dep)

