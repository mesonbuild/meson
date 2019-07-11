## Version check in `find_program()`

A new `version` keyword argument has been added to `find_program` to specify
the required version. See [`dependency()`](#dependency) for argument format.
The version of the program is determined by running `program_name --version`
command. If stdout is empty it fallbacks to stderr. If the output contains more
text than simply a version number, only the first occurence of numbers separated
by dots is kept. If the output is more complicated than that, the version
checking will have to be done manually using [`run_command()`](#run_command).
