## Use fallback from wrap file when force fallback

Optional dependency like below will now fallback to the subproject
defined in the wrap file in the case `wrap_mode` is set to `forcefallback`
or `force_fallback_for` contains the subproject.

```meson
# required is false because we could fallback to cc.find_library(), but in the
# forcefallback case this now configure the subproject.
dep = dependency('foo-1.0', required: false)
if not dep.found()
  dep = cc.find_library('foo', has_headers: 'foo.h')
endif
```

```ini
[wrap-file]
...
[provide]
dependency_names = foo-1.0
```
