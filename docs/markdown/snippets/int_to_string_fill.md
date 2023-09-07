## Added 'fill' kwarg to int.to_string()

int.to_string() now accepts a `fill` argument. This allows you to pad the
string representation of the integer with leading zeroes:

```meson
n = 4
message(n.to_string())
message(n.to_string(length: 3))

n = -4
message(n.to_string(length: 3))
```

OUTPUT:
```meson
4
004
-04
```