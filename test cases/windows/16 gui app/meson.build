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

tool = find_program('objdump', 'dumpbin', required: false)
# TODO: when 'llvm-objdump -f' emits the subsystem type, we could use that also

if tool.found()
  test('is_gui', tester, args: [tool.path(), gui_prog, '2'])
  test('not_gui', tester, args: [tool.path(), console_prog, '3'])
endif
