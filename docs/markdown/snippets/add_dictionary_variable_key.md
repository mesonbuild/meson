## Adding dictionary entry using string variable as key

New dictionary entry can now be added using string variable as key, 
in addition to using string literal as key.

```meson
dict = {}

# A variable to be used as a key
key = 'myKey'

# Add new entry using the variable
dict += {key : 'myValue'}

# Test that the stored value is correct 
assert(dict[key] == 'myValue', 'Incorrect value retrieved from dictionary')
```
