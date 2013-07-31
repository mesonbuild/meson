project('alignment', 'c')

cc = meson.get_compiler('c')

# These tests should return the same value on all
# platforms. If (and when) they don't, fix 'em up.
if cc.alignment('char') != 1
  error('Alignment of char misdetected.')
endif

ptr_size = cc.sizeof('void*')
dbl_alignment = cc.alignment('double')

if ((ptr_size == 4) and (dbl_alignment == 4)) or ((ptr_size == 8) and (dbl_alignment == 8))
  message('Alignment of double ok.')
else
  error('Alignment of double erroneous.')
endif
