project('vcstag', 'c')

version_src = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag.c',
fallback : '1.0.0')

version_src_custom = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom.c',
command : ['git', 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')

executable('tagprog', 'tagprog.c', version_src)
executable('tagprog-custom', 'tagprog.c', version_src_custom)

