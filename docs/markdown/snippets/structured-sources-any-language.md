## `structured_sources()` can be used with any language

[[structured_sources]] previously only worked with Rust build targets
and Java resources, and raised an error otherwise. It can now be used
with a target of any language (other than Java, where it can only be
used for resources like before).

Files will be laid out in the build directory according to the structure
described by the dictionary keys; for example, in the case of C
it will be possible to include a file from the `structured_sources()`
from another according to their provided path.
