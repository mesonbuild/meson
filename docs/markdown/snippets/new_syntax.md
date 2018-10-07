## Foreach `break` and `continue`

`break` and `continue` keywords can be used inside foreach loops.

```meson
items = ['a', 'continue', 'b', 'break', 'c']
result = []
foreach i : items
  if i == 'continue'
    continue
  elif i == 'break'
    break
  endif
  result += i
endforeach
# result is ['a', 'b']
```

You can check if an array contains an element like this:
```meson
my_array = [1, 2]
if 1 in my_array
# This condition is true
endif
if 1 not in my_array
# This condition is false
endif
```

You can check if a dictionary contains a key like this:
```meson
my_dict = {'foo': 42, 'foo': 43}
if 'foo' in my_dict
# This condition is true
endif
if 42 in my_dict
# This condition is false
endif
if 'foo' not in my_dict
# This condition is false
endif
```
