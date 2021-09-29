## Comparing two objects with different types is now an error

Using the `==` and `!=` operators to compare objects of different (for instance
`[1] == 1`) types was deprecated and undefined behavior since 0.45.0 and is
now a hard error.
