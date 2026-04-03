## `rc` is now a first-class language

Windows resource compilation (`.rc` files) is now supported as a proper
Meson language. See [RC](RC.md) for full documentation.

## `windows.compile_resources()` is deprecated

`windows.compile_resources()` is deprecated in favor of the new `rc`
language. Calls to it will emit a deprecation warning. The function
continues to work as a thin compatibility shim that delegates to the
`rc` language pipeline internally, so existing projects will not break.
See [Windows module](Windows-module.md#compile_resources) for migration
guidance.
