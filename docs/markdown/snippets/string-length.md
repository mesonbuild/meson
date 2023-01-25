## String `length()` method

Added a method to get the length of a string, it can be used to check for
variables length assumptions or to go through the string char-by-char.

```meson
str = 'string'
assert(str.length() == 6)

foreach c: range(str.length())
  message(c)
endforeach
```
