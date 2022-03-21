## Per-subproject languages

Subprojects does not inherit languages added by main project or other subprojects
any more. This could break subprojects that wants to compile e.g. `.c` files but
did not add `c` language, either in `project()` or `add_languages()`, and were
relying on the main project to do it for them.
