project('add dictionary entry using string variable as key', meson_version: '>=0.52')

dict = {}

# A variable to be used as a key
key = 'myKey'

# Add new entry using the variable
dict += {key : 'myValue'}

# Test that the stored value is correct 
assert(dict[key] == 'myValue', 'Incorrect value retrieved from dictionary')
