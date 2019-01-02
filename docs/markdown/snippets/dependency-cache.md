## Consistent return value of `dependency()`

The return value of `dependency('somedep')` is now cached and the same value
will always be returned, even in subprojects, regardless of the version required
and the presence (or not) of the fallback keyword argument. However, if different
calls to `dependency()` differs by the `module` keyword argument, they are cached
separately and will not return the same value.

### Implications

Let's assume the system has `glib-2.0` version 2.40 installed with its pkg-config
file, and we configure a project with multiple subprojects that all depends on
different versions of glib.

- If the first call is `dependency('glib-2.0', version : '>=2.40')`, the
dependency will be satisfied by the system version found using pkg-config.
If a 2nd call then does `dependency('glib-2.0', version : '>=2.50', fallback : ['glib', 'glib_dep'])`,
Meson used to configure the fallback subproject because the system dependency does
not satisfy the required version, leading to different parts of the project linking
on different version of glib. Meson will now instead abort because the cached
dependency object from the first call does not satisfy the requested version in
the 2nd call for consistency.

- If the first call is `dependency('glib-2.0', version : '>=2.50', fallback : ['glib', 'glib_dep'])`
Meson will configure the fallback subproject because the system dependency does
not satisfy the required version. If a 2nd call then does
`dependency('glib-2.0', version : '>=2.40')`, Meson used to return the system
dependency because it miss the fallback keyword argument. Meson will now instead
return the glib subproject dependency instead for consistency. Likewise if the
2nd call is `dependency('glib-2.0', version : '>=2.50')` Meson used to abort
because the system dependency version is too old, but it will now instead return
the dependency from glib subproject.

- If the first call is `dependency('glib-2.0', version : '>=2.50', required : false)`
it returns a not-found dependency object because the system version is too old
and there is no fallback provided. If a 2nd call then does
`dependency('glib-2.0', version : '>=2.50', fallback : ['glib', 'glib_dep'])`,
Meson used to configure the fallback subproject, leading to some parts of
the project to not enable their optional glib support even though we do have glib
in the end. Meson will now instead return a not-found dependency in the 2nd call
for consistency.

- However, if the first call is `dependency('glib-2.0', required : get_option('glib_opt'))`,
and `glib_opt` is a `disabled` feature option, the returned not-found dependency
object is NOT cached. A 2nd call to `dependency('glib-2.0', version : '>=2.40')`
will return the system dependency.

It is parent project's responsability to ensure that the first lookup of a
dependency has the proper `fallback` keyword argument.
