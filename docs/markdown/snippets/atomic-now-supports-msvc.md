## Custom dependency for atomic now works on MSVC

`dependency('atomic')` now works on MSVC >=19.35.32124.
It requires `c_std=c11` or later, otherwise the dependency will return not found.
