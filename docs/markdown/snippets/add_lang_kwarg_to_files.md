## Add 'lang' kwarg to files

The `files` method has a new kwarg `lang` that allows the client to specify 
explicitly the compiler to use for the list of sources. This will bypass the 
automatic language detection performed by meson. If the kwarg is not specified, 
existing behavior is maintained.
