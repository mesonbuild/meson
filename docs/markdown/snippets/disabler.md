## Return `Disabler()` instead of not-found object

Functions such as `dependency()`, `find_library()`, `find_program()`, and
`python.find_installation()` have a new keyword argument: `disabler`. When set
to `true` those functions return `Disabler()` objects instead of not-found
objects.
