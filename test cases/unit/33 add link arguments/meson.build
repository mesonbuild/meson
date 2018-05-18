project('add link arguments', 'c')

add_project_link_arguments('-Wl,broken1')
add_project_link_arguments('-Wl,broken2', language : 'c')
add_project_link_arguments('-Wl,broken3', language : 'cpp')

executable('testapp', 'test.c')
