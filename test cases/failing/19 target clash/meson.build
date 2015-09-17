project('clash', 'c')

# This setup causes a namespace clash when two Meson targets would
# produce a Ninja targets with the same name. It only works on
# unix, because on Windows the target has a '.exe' suffix.
#
# This test might fail to work on different backends or when
# output location is redirected.

if host_machine.system() == 'windows'
  error('This is expected.')
endif

executable('clash', 'clash.c')
run_target('clash', 'echo', 'clash 1')
