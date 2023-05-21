## `generator.process(generator.process(...))`

Added support for code like this:
```meson
gen1 = generator(...)
gen2 = generator(...)
gen2.process(gen1.process('input.txt'))
```
