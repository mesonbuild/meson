## Call for testing for next release

At the beginning of next cycle we aim to merge the [option refactor
branch](https://github.com/mesonbuild/meson/pull/13441). This is a
_huge_ change that will touch pretty much all code.

The main change it brings is that you can override any builtin option
value for any subproject (even the top one) entirely from the command
line. This means that you can, for example, enable optimizations on
all subprojects but not on the top level project.

We have done extensive testing and all our tests currently
pass. However it is expected that this will break some workflows. So
please test the branch when it lands and report issues. We want to fix
all regressions as soon as possible, preferably far before the next rc
release.
