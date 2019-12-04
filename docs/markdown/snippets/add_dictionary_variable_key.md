## Dictionary entry using string variable as key

Keys can now be any expression evaluating to a string value, not limited
to string literals any more.
```meson
d = {'a' + 'b' : 42}
k = 'cd'
d += {k : 43}
```
