## A dictionary key named `kwargs` is no longer expanded

A dictionary literal such as `{'kwargs': {'env': {'CFLAGS': '-DFOO'}}}` used to
be evaluated as if `kwargs` were the special keyword argument of function
calls, and the value of the dictionary was replaced with the contents of the
nested dictionary.  The `kwargs` key is now a normal key in dictionary
literals, and is only special in the arguments of a function or method call.
This also makes it possible to write `func(kwargs: d['kwargs'])`.
