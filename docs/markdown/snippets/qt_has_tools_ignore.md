## Tools can be skipped when calling `has_tools()` on the Qt modules

When checking for the presence of Qt tools, you can now ask Meson to not check
for the presence of a list of tools. This is particularly useful when you do
not need `lrelease` because you are not shipping any translations. For example:

```meson
qt6_mod = import('qt6')
qt6_mod.has_tools(required: true, skip: ['lrelease'])
```
