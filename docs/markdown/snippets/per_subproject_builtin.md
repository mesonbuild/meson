## Per subproject `default_library` option

The `default_library` built-in option can now be defined per subproject. This is
useful for example when building shared libraries in the main project, but static
link a subproject.

Most of the time this would be used either by the parent project by setting
subproject's default_options (e.g. `subproject('foo', default_options: 'default_library=static')`),
or by the user using the command line `-Dfoo:default_library=static`.

The value is overriden in this order:
- Value from parent project
- Value from subproject's default_options if set
- Value from subproject() default_options if set
- Value from command line if set
