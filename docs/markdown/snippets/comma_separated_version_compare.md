## `version_compare` now accept comma-separated strings

 Now, it is possible to compare version against multiple values separated by comma, to check for a range of version for instance or exclude specific versions.

 ```meson
 '1.5'.version_compare('>=1,<2,!=1.4.1')
 ```
