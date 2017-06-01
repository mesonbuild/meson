project('slashname', 'c',
  meson_version : '>=0.40.0')

# Traverse this subdir so the corresponding dir
# is created inside the build dir.
subdir('sub')

# Try to create an executable that would go in the "sub" dir
# inside the build dir. This is prohibited.
executable('sub/prog', pf)
