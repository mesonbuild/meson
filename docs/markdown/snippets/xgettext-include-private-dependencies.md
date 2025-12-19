## i18n.xgettext recursive option now includes "private" dependencies

Suppose we have:

```
libA.dll -> libB.dll -> libC.dll
```

Here, `libA` links with `libB`, and `libB` links with `libC`, but `libA` does
not link with `libC` directly. So, `libC` is a "private" dependency of `libB`.
If we collect strings to translate using:

```
i18n.xgettext(libC)
i18n.xgettext(libB)
pot_file = i18n.xgettext(libA, recursive: true)
```

Previously, strings from `libC` would not be included in `pot_file`, since
`libC` is not a direct link dependency of `libA`. This has been fixed: when
the `recursive: true` option is used, `xgettext` now recursively includes
translations from all dependencies, including those of dependencies. This is
more logical, as even if `libA` does not directly link with `libC`, it may
still need translated strings from `libC`.
