project('vcstag', 'c')

version_src = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag.c',
fallback : '1.0.0')

executable('tagprog', 'tagprog.c', version_src)

