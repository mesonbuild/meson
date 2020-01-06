project('curses', 'c')

curses = dependency('curses', required: false)
if not curses.found()
  error('MESON_SKIP_TEST: Curses library not found')
endif

exec = executable('basic', 'main.c', dependencies: curses)
# didn't run the test because in general graphics fail on CI
