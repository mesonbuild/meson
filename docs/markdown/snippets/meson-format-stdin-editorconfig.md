## meson format now has a --source-file-path argument when reading from stdin

This argument is mandatory to mix stdin reading with the use of editor config.
It allows to know where to look for the .editorconfig, and to use the right
section of .editorconfig based on the parsed file name.
