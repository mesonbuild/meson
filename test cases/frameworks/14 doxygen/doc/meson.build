cdata.set('TOP_SRCDIR', meson.source_root())
cdata.set('TOP_BUILDDIR', meson.build_root())

wrapper_script = find_program('doxyrunner.py')

doxyfile = configure_file(input: 'Doxyfile.in',
                          output: 'Doxyfile',
                          configuration: cdata,
                          install: false)

datadir = join_paths(get_option('datadir'), 'doc', 'spede')

opaque_target('spede-docs',
              command: wrapper_script,
              args: [doxyfile],
              install: true,
              install_dir: datadir)
