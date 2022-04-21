## Deprecate an option and replace it with a new one

The `deprecated` keyword argument can now take the name of a new option
that replace this option. In that case, setting a value on the deprecated option
will set the value on both the old and new names, assuming they accept the same
values.

```meson
# A boolean option has been replaced by a feature with another name, old true/false values
# are accepted by the new option for backward compatibility.
option('o1', type: 'boolean', value: 'true', deprecated: 'o2')
option('o2', type: 'feature', value: 'enabled', deprecated: {'true': 'enabled', 'false': 'disabled'})

# A project option is replaced by a module option
option('o3', type: 'string', value: '', deprecated: 'python.platlibdir')
```
