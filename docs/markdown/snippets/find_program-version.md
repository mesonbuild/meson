## found programs now have a version method

The return value of [[find_program]] can now check the exact version of the
found program, independent of the minimum version requirement. This can be used
e.g. to perform different actions depending on the exact version detected.
