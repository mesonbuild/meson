## Compilers now have a `has_define` method

This method returns true if the given preprocessor symbol is
defined, else false is returned. This is useful is cases where
an empty define has to be distinguished from a non-set one, which
is not possible using `get_define`.

Additionally it makes intent clearer for code that only needs
to check if a specific define is set at all and does not care
about its value.