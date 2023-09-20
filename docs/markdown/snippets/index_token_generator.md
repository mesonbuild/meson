## `@INDEX@` in generator()'s args and output

The `@INDEX@` special string can now be used in `generator()`'s `args` and `output` keyword arguments.
When utilizing `generator.process()` on a list of files, `@INDEX@` will be replaced by the index of the 
current file being processed, starting from 0. The index will be padded with leading zeroes based on the
total number of inputs, ensuring a consistent width for easy parsing and handling.