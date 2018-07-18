## Dictionary addition

Dictionaries can now be added, values from the second dictionary overrides values
from the first

```meson
d1 = {'a' : 'b'}
d3 = d1 + {'a' : 'c'}
d3 += {'d' : 'e'}
```
