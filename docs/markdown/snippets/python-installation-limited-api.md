## Add `limited_api` keyword support to `find_installation()` and `dependency()`

The `find_installation()` function in the Python module and the
`dependency()` method on Python installation objects now support the
`limited_api` keyword argument. The installation's value is inherited
by the `extension_module()` and `dependency()` methods by default but
can be overridden.

This allows building libraries (or any targets) against the Python
Limited API even if those targets are not Python extensions.
