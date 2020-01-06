project('pie options', 'c')

opt = get_option('pie_str')
if opt == ''
  opt = get_option('pie_bool')
endif

executable('trivial', 'trivial.c', pie : opt)
