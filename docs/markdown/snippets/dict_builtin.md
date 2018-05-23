## New built-in object dictionary

Meson dictionaries use a syntax similar to python's dictionaries,
but have a narrower scope: they are immutable, keys can only
be string literals, and initializing a dictionary with duplicate
keys causes a fatal error.

Example usage:

```meson
dict = {'foo': 42, 'bar': 'baz'}

foo = dict.get('foo')
foobar = dict.get('foobar', 'fallback-value')

foreach key, value : dict
  Do something with key and value
endforeach
```
