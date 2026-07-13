## External programs as inputs and dependencies to custom targets

Custom targets now allow specifying an external program in
the `input` and `depends` keyword arguments.  This also applies
to several methods provided by modules, as they are lowered to
custom targets internally.

## External programs as dependencies to tests

Tests now allow specifying an external program in
the `depends` keyword argument.

