project('gui_app_test', 'c')

#
# test that linking a Windows console applications with the main function in a
# library is correctly instructed which entrypoint function to look for
#

console_lib = static_library('main', 'console_prog.c')
executable('console', 'dummy.c', link_with: console_lib, gui_app: false)
