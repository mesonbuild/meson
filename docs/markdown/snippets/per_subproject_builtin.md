## Per subproject `default_library` and `werror` options

The `default_library` and `werror` built-in options can now be defined per subproject.
This is useful for example when building shared libraries in the main project,
but static link a subproject, or when the main project must build with no warnings
but some subprojects cannot.

Most of the time this would be used either by the parent project by setting
subproject's default_options (e.g. `subproject('foo', default_options: 'default_library=static')`),
or by the user using the command line `-Dfoo:default_library=static`.

The value is overriden in this order:
- Value from parent project
- Value from subproject's default_options if set
- Value from subproject() default_options if set
- Value from command line if set
