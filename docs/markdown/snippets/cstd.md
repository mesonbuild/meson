## c_std and cpp_std options now accepts a list of values

Projects that prefer GNU C but can fallback to ISO C can now set for
example `default_options: 'c_std=gnu11,c11'` and it will use gnu11 when
available, fallback to c11 otherwise. It is an error only if none of the
values are supported by the current compiler.

Likewise, a project that can take benefit of `c++17` but can still build with
`c++11` can set `default_options: 'cpp_std=c++17,c++11'`.

This allows to deprecate gnuXX values from MSVC compiler, that means
that `default_options: 'c_std=gnu11'` will now print warning with MSVC
but still fallback to 'c11' value. No warning is printed if at least one
of the values is valid, i.e. `default_options: 'c_std=gnu11,c11'`.

In the future that deprecation warning will become an hard error because
`c_std=gnu11` should mean GNU is required, for projects that cannot be
built with MSVC for example.
