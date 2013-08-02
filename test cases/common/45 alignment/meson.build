project('alignment', 'c')

cc = meson.get_compiler('c')

# These tests should return the same value on all
# platforms. If (and when) they don't, fix 'em up.
if cc.alignment('char') != 1
  error('Alignment of char misdetected.')
endif

ptr_size = cc.sizeof('void*')
dbl_alignment = cc.alignment('double')

if host.name() == 'windows'
  dbl_exp = 8
else
  dbl_exp = ptr_size
endif

if dbl_alignment == dbl_exp
  message('Alignment of double ok.')
else
  error('Alignment of double misdetected.')
endif
