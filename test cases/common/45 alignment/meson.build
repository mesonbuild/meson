project('alignment', 'c')

cc = meson.get_compiler('c')

# These tests should return the same value on all
# platforms. If (and when) they don't, fix 'em up.
if cc.alignment('char') != 1
  error('Alignment of char misdetected.')
endif

if cc.alignment('double') != 8
  error('Alignment of double misdetected.')
endif
