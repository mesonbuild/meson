project('trivial test', 'c')
exe = executable('trivialprog', 'trivial.c')
runt = run_target('invalid', command: ['echo', 'run_target'])
meson.add_install_script(exe, runt)
