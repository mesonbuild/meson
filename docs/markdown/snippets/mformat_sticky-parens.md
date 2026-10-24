## sticky_parens format option

A new `sticky_parens` option for the `meson format` command now sticks the
parentheses to the outer expression instead of putting them on their own line,
and double-indents continuation lines of the expression.

With `sticky_parens = false` (default):

```meson
if (
    host_machine.system() == 'windows'
    or host_machine.system() == 'cygwin'
    or host_machine.system() == 'darwin'
)
    message('...')
endif
```

With `sticky_parens = true`:

```meson
if (host_machine.system() == 'windows'
        or host_machine.system() == 'cygwin'
        or host_machine.system() == 'darwin')
    message('...')
endif
```
