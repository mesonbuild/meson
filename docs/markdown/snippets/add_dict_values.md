## Added a `values()` method for dictionaries

Mesons built-in [[@dict]] type now supports the [[dict.values]] method
to retrieve the dictionary values as an array, analogous to the
[[dict.keys]] method.

```meson
dict = { 'b': 'world', 'a': 'hello' }

[[#dict.keys]] # Returns ['a', 'b']
[[#dict.values]] # Returns ['hello', 'world']
```
