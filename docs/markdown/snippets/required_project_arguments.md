# Required project & global arguments

The `add_global_arguments` & `add_project_arguments` functions now
support an optional keyword argument named `required`. Setting it
to `true` will cause Meson to perform compiler support checks on
each of the passed arguments as if by calling `has_argument`, which
means manual checks can now be avoided and instead expressed more
tersely.
