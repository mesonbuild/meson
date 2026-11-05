project('29 object library pic', 'c')

cm = import('cmake')
sub_pro = cm.subproject('cmTest')
sub_dep = sub_pro.dependency('cmTestLib')

shared_library('slib', 'slib.c', dependencies: sub_dep)
