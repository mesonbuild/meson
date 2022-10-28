## `in` operator for strings

`in` and `not in` operators now works on strings, in addition to arrays and
dictionaries.

```
fs = import('fs')
if 'something' in fs.read('somefile')
  # True
endif
```
