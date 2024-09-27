## Tools can be selected when calling `has_tools()` on the Qt modules

When checking for the presence of Qt tools, you can now explictly ask Meson
which tools you need. This is particularly useful when you do not need
`lrelease` because you are not shipping any translations. For example:

```meson
qt6_mod = import('qt6')
qt6_mod.has_tools(required: true, tools: ['moc', 'uic', 'rcc'])
```

valid tools are `moc`, `uic`, `rcc` and `lrelease`.
