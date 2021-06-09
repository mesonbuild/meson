project('header install')

as_array = ['subdir.h']

subdir('vanishing_subdir')
subdir('sub')

h1 = install_headers('rootdir.h')
h2 = install_headers(as_array, subdir : 'subdir')
h3 = install_headers(subheader)
h4 = install_headers(disabler())
