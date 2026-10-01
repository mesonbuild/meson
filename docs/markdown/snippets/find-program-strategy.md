## New search order for `find_program()`

`find_program()` searches for programs in machine files and in the system;
starting with Meson 1.13.0, the search process is applied separately for
each name passed to the function:

- If the first name is defined in a machine file, Meson uses that entry.

- Otherwise, Meson searches for the first name in the project's source tree,
  the directories listed in `dirs:`, and `PATH`.

- If the program is not found or does not satisfy the requested version,
  Meson tries the next name.

Previous versions of Meson looked for all names in the machine files first.
Meson never searched for the program in the system if the machine file
pointed to one of the programs, using the program in the machine file
even if it did not satisfy the version requirement in `meson.build`.
Likewise, if no name was in a machine file, the search stopped at the first
name found in the system, even if a later name would have satisfied the
version requirement.
