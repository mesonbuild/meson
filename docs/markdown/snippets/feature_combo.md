## Feature combo

A new option type has been added: [`feature-combo`](Build-options.md#feature_combos).

Example:
```meson
option('3d-backend', type : 'feature-combo', choices : ['gl', 'gles', 'vulkan'], value : 'auto')
...
gl_dep = dependency('gl', required : get_option('3d-backend:gl'))
vulkan_dep = dependency('vulkan', required : get_option('3d-backend:vulkan'))
```
