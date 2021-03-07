## Introducing format strings to the Meson language

In addition to the conventional `'A string @0@ to be formatted @1@'.format(n, m)`
method of formatting strings in the Meson language, there's now the additional
`f'A string @n@ to be formatted @m@'` notation that provides a non-positional
and clearer alternative. Meson's format strings are currently restricted to
identity-expressions, meaning `f'format @'m' + 'e'@'` will not parse.
