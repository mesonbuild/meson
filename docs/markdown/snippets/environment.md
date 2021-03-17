## Multiple append() and prepend() in `environment()` object

`append()` and `prepend()` methods can now be called multiple times
on the same `varname`. Earlier Meson versions would warn and only the last
opperation was taking effect.

```meson
env = environment()

# MY_PATH will be '0:1:2:3'
env.set('MY_PATH', '1')
env.append('MY_PATH', '2')
env.append('MY_PATH', '3')
env.prepend('MY_PATH', '0')
```

