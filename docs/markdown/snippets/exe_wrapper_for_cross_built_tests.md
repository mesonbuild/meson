## Test scripts are given the exe wrapper if needed

Meson will now set the `MESON_EXE_WRAPPER` as the properly wrapped and joined
representation. For Unix-like OSes this means python's shelx.join, on Windows
an implementation that attempts to properly quote windows argument is used.
This allow wrapper scripts to run test binaries, instead of just skipping.

for example, if the wrapper is `['emulator', '--script']`, it will be passed
as `MESON_EXE_WRAPPER="emulator --script"`.
