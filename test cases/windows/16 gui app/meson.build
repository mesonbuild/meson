project('gui_app_test', 'c')

#
# test that linking a Windows console applications with the main function in a
# library is correctly instructed which entrypoint function to look for
#

console_lib = static_library('main', 'console_prog.c')
executable('console', 'dummy.c', link_with: console_lib, gui_app: false)

#
# also verify that the correct subsystem is set by executable(gui_app:)
#

gui_prog = executable('gui_prog', 'gui_prog.c', gui_app: true)
console_prog = executable('console_prog', 'console_prog.c', gui_app: false)

tester = find_program('gui_app_tester.py')

test('is_gui', tester, args: [gui_prog, '2'])
test('not_gui', tester, args: [console_prog, '3'])
