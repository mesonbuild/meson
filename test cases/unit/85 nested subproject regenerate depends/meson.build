project('nested subproject regenerate depends', 'c')

s = subproject('sub1')

# This is needed to make msbuild noop check work correctly
executable('exe', 'main.c')
