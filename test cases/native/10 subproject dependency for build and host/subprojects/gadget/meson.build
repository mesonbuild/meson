project('gadget', 'c', version : '1.0')

cc = meson.get_compiler('c')

cdata = configuration_data()
cdata.set('GADGET_LIMIT', get_option('limit'))

configure_file(output : 'config.h',
               configuration : cdata)
add_project_arguments(cc.get_argument_syntax() == 'msvc' ? '/FI' : '-include',
                      meson.current_build_dir() / 'config.h',
                      language : 'c')

gadget = library('gadget', 'gadget.c',
                 install : true)
gadget_dep = declare_dependency(link_with : gadget,
                                include_directories : include_directories('.'))

meson.override_dependency('gadget', gadget_dep)
