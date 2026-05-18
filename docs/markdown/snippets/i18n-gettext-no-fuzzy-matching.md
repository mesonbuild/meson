## New `no_fuzzy_matching` keyword argument for `i18n.gettext()`

`i18n.gettext()` now accepts a `no_fuzzy_matching` boolean keyword argument
that, when set to `true`, passes `--no-fuzzy-matching` to `msgmerge`. This
prevents `msgmerge` from auto-generating fuzzy translations for new strings,
which are almost always incorrect.

```meson
i18n.gettext('myproject',
             preset : 'glib',
             no_fuzzy_matching : true)
```
