## A machine file may be used to pass extra arguments to clang in a bindgen call

Because of the way that bindgen proxies arguments to clang the only choice to
add extra arguments currently is to wrap bindgen in a script, since the
arguments must come after a `--`. This is inelegant, and not very portable. Now
a `bindgen_clang_arguments` field may be placed in the machine file for the host
machine, and these arguments will be added to every bindgen call for clang. This
is intended to be useful for things like injecting `--target` arguments.
