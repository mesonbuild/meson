## New encoding keyword for configure_file

Add a new keyword to [`configure_file()`](#Reference-manual.md#configure_file)
that allows the developer to specify the input and output file encoding.

If the file encoding of the input is not UTF-8 meson can crash (see #1542).
A crash as with UTF-16 is the best case and the worst meson will silently
corrupt the output file for example with ISO-2022-JP. For additional details
see pull request #3135.

The new keyword defaults to UTF-8 and the documentation strongly suggest to
convert the file to UTF-8 when possible.
