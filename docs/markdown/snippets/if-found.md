# Added `if_found` to subdir

Added a new keyword argument to the `subdir` command. It is given a
list of dependency objects and the function will only recurse in the
subdirectory if they are all found. Typical usage goes like this.

    d1 = dependency('foo') # This is found
    d2 = dependency('bar') # This is not found

    subdir('somedir', if_found : [d1, d2])

In this case the subdirectory would not be entered since `d2` could
not be found.
