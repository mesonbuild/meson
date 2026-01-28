## windows.compile_resources now detects header changes with rc.exe

The `rc.exe` resource compiler neither provides *depfile* support nor
allows showing includes, as is possible with C or C++ compilers.
Therefore, changes to files included by the `.rc` file did not trigger
recompilation of the resource file.

A workaround was added to *meson* by calling the preprocessor on the
`.rc` file to display the included headers and allow ninja to record them
as dependencies.
