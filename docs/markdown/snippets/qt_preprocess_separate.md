## Separate functions for qt preprocess

`qt.preprocess` is a large, complicated function that does a lot of things,
a new set of `compile_*` functions have been provided as well. These are
conceptually simpler, as they do a single thing.
