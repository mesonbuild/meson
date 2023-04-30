project('link with preprocess', 'c')

cc = meson.get_compiler('c')

pp_files = cc.preprocess('foo.c')

bar = executable('bar', 'bar.c', link_with: pp_files)
