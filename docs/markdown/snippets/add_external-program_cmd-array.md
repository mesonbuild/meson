## Add cmd_array method to ExternalProgram

Added a new `cmd_array()` method to the `ExternalProgram` object that returns
an array containing the command(s) for the program. This is particularly useful
in cases like pyInstaller where the Python command is `meson.exe runpython`,
and the full path should not be used but rather the command array.

The method returns a list of strings representing the complete command needed
to execute the external program, which may differ from just the full path
returned by `full_path()` in cases where wrapper commands or interpreters are
involved.
