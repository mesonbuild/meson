project('bar', 'c', license: 'Apache')

executable('bar', 'bar.c')

license = meson.project_license()[0]
if license != 'Apache'
    error('The license should be Apache, but it is: ' + license)
endif
