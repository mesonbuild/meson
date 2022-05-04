## Add the `strict` keyword argument to `FeatureOption.disable_auto_if()`

In some cases it's desireable for a Feature to become disabled only if a
condition is true, but a related case is to *require* a feature to become
disabled if a condition is true.

This generally leads to code like:
```meson
feat = get_option('feat').disable_auto_if(true)
if not feat.disabled()
  error(...)
endif
```

It it's more convenient to rewrite that as:
```meson
feat = get_option('feat').disable_auto_if(true, strict : true, error_message : ...)
```

This becomes especially true when such options need to be chained together:
```meson
feat = get_option('feat')
if feat.allowed()
  feat = feat.disable_auto_if(not dep1.found())
  if not feat.disabled()
    error(require dep1 for feat!')
  endif

  feat = feat.disable_auto_if(not dep2.found())
  if not feat.disabled()
    error(require dep2 for feat!')
  endif
endif
```
becomes
```meson
feat = get_option('feet') \
       .disable_auto_if(not dep1.found(), strict : true, error_message : 'require dep1 for feat!') \
       .disable_auto_if(not dep2.found(), strict : true, error_message : 'require dep2 for feat!') \
       .disabled()
```
