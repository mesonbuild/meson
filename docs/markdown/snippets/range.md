## New `range()` function

``` meson
    rangeobject range(stop)
    rangeobject range(start, stop[, step])
```

Return an opaque object that can be only be used in `foreach` statements.
- `start` must be integer greater or equal to 0. Defaults to 0.
- `stop` must be integer greater or equal to `start`.
- `step` must be integer greater or equal to 1. Defaults to 1.

It cause the `foreach` loop to be called with the value from `start` included
to `stop` excluded with an increment of `step` after each loop.

```meson
# Loop 15 times with i from 0 to 14 included.
foreach i : range(15)
   ...
endforeach
```

The range object can also be assigned to a variable and indexed.
```meson
r = range(5, 10, 2)
assert(r[2] == 9)
```

