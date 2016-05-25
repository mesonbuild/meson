project('gtkdoctest', 'c')

gnome = import('gnome')

assert(gnome.gtkdoc_html_dir('foobar') == 'share/gtkdoc/html/foobar', 'Gtkdoc install dir is incorrect.')

inc = include_directories('include')

# We have to disable this test until this bug fix has landed to
# distros https://bugzilla.gnome.org/show_bug.cgi?id=753145
# subdir('doc')
