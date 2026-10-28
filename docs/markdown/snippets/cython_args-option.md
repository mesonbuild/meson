## The `cython_args` option is passed to the Cython compiler

The `cython_args` built-in option, set with `-Dcython_args=...` or in a machine
file, was ignored when translating `.pyx` files to C.  It is now added to the
Cython command line, together with the `cython_args` keyword argument of the
target.
