project('add dictionary entry using string variable as key', meson_version: '>=0.52')

dict1 = {}

# A variable to be used as a key
testkey1 = 'myKey1'
testkey2 = 'myKey2'

# Add new entry using the variable
dict1 += {testkey1 : 'myValue'}
dict1 += {testkey2 : 42}

# Test that the stored values are correct
assert(dict1[testkey1] == 'myValue',
       'Incorrect string value retrieved from dictionary - variable key')
assert(dict1['myKey1'] == 'myValue',
       'Incorrect string value retrieved from dictionary - literal key')
assert(dict1[testkey2] == 42,
       'Incorrect int value retrieved from dictionary - variable key')
assert(dict1['myKey2'] == 42,
       'Incorrect int value retrieved from dictionary - literal key')
