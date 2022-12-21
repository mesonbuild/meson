## Add a FeatureOption.enable_if and .disable_if

These are useful when features need to be constrained to pass to [[dependency]],
as the behavior of an `auto` and `disabled` or `enabled` feature is markedly
different. consider the following case:

```meson
opt = get_option('feature').disable_auto_if(not foo)
if opt.enabled() and not foo
  error('Cannot enable feat when foo is not also enabled')
endif
dep = dependency('foo', required : opt)
```

This could be simplified to
```meson
opt = get_option('feature').disable_if(not foo, error_message : 'Cannot enable feature when foo is not also enabled')
dep = dependency('foo', required : opt)
```

For a real life example, here is some code in mesa:
```meson
_llvm = get_option('llvm')
dep_llvm = null_dep
with_llvm = false
if _llvm.allowed()
  dep_llvm = dependency(
    'llvm',
    version : _llvm_version,
    modules : llvm_modules,
    optional_modules : llvm_optional_modules,
    required : (
      with_amd_vk or with_gallium_radeonsi or with_gallium_opencl or with_clc
      or _llvm.enabled()
    ),
    static : not _shared_llvm,
    fallback : ['llvm', 'dep_llvm'],
    include_type : 'system',
  )
  with_llvm = dep_llvm.found()
endif
if with_llvm
  ...
elif with_amd_vk and with_aco_tests
  error('ACO tests require LLVM, but LLVM is disabled.')
elif with_gallium_radeonsi or with_swrast_vk
  error('The following drivers require LLVM: RadeonSI, SWR, Lavapipe. One of these is enabled, but LLVM is disabled.')
elif with_gallium_opencl
  error('The OpenCL "Clover" state tracker requires LLVM, but LLVM is disabled.')
elif with_clc
  error('The CLC compiler requires LLVM, but LLVM is disabled.')
else
  draw_with_llvm = false
endif
```

simplified to:
```meson
_llvm = get_option('llvm') \
  .enable_if(with_amd_vk and with_aco_tests, error_message : 'ACO tests requires LLVM') \
  .enable_if(with_gallium_radeonsi, error_message : 'RadeonSI requires LLVM') \
  .enable_if(with_swrast_vk, error_message : 'Vulkan SWRAST requires LLVM') \
  .enable_if(with_gallium_opencl, error_message : 'The OpenCL Clover state trackers requires LLVM') \
  .enable_if(with_clc, error_message : 'CLC library requires LLVM')

dep_llvm = dependency(
  'llvm',
  version : _llvm_version,
  modules : llvm_modules,
  optional_modules : llvm_optional_modules,
  required : _llvm,
  static : not _shared_llvm,
  fallback : ['llvm', 'dep_llvm'],
  include_type : 'system',
)
with_llvm = dep_llvm.found()
```
