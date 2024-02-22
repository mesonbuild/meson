# Features Module

This module provides functions for advanced feature option interactions. It is
new in Meson 1.2.0

## new

Create a new feature option object with a given name and value:
```meson
feat = import('feature').new('name', 'auto')
```

## any

Provides a mechanism to provide or-like checking. Due to the `mode` option it can be tailored to or the objects to the user's expectations. It returns a boolean, and is best combined with `new` if you want to replace a provided feature.

The mode keyword argument must be one of:
 - "auto": feat.is_auto() == true
 - "enabled": feat.is_enabled() == true
 - "disabled": feat.is_disabled() == true
 - "allowed": feat.is_disabled() == false
 - "denied": feat.is_enabled() == true

and defaults to "auto"

```meson
f1 = get_option('f1')
f2 = get_option('f2')

feat = import('features')

if not feat.any(f1, f2, mode : 'allowed')
  error('f1 or f2 must be enabled')
endif
```

## and

Provides a mechanism to provide and-like checking. Due to the `mode` option it can be tailored to or the objects to the user's expectations. It returns a boolean, and is best combined with `new` if you want to replace an object.

The mode keyword argument must be one of:
 - "auto": feat.is_auto() == true
 - "enabled": feat.is_enabled() == true
 - "disabled": feat.is_disabled() == true
 - "allowed": feat.is_disabled() == false
 - "denied": feat.is_enabled() == true

and defaults to "auto"

```meson
f1 = get_option('f1')
f2 = get_option('f2')

feat = import('features')

if feat.all(f1, f2, mode : 'disabled')
  error('f1 or f2 must be enabled')
endif
```
