## Dependencies with multiple names

More than one name can now be passed to `dependency()`, they will be tried in order
and the first name to be found will be used. The fallback subproject will be
used only if none of the names are found on the system. Once one of the name has
been found, all other names are added into the cache so subsequent calls for any
of those name will return the same value. This is useful in case a dependency
could have different names, such as `png` and `libpng`.
