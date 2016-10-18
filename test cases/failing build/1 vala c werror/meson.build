project('valatest', 'c', default_options : 'werror=true')

if find_program('valac', required : false).found()
  add_languages('vala')
  valadeps = [dependency('glib-2.0'), dependency('gobject-2.0')]
  # Must fail due to -Werror and unused variable in C file
  executable('valaprog', 'prog.vala', 'unused-var.c', dependencies : valadeps)
else
  executable('failprog', 'unused-var.c')
endif
