project('devenv', 'c')

meson.add_devenv('TEST_A=1')
foo_dep = dependency('foo', fallback: 'sub')

env = environment()
env.append('TEST_B', ['2', '3'], separator: '+')
meson.add_devenv(env)

# This exe links on a library built in another directory. On Windows this means
# PATH must contain builddir/subprojects/sub to be able to run it.
executable('app', 'main.c', dependencies: foo_dep, install: true)
