## More flexible `override_find_program()`.

It is now possible to pass an `executable` to
`override_find_program()` if the overridden program is not used during
configure.

This is particularly useful for fallback dependencies like Protobuf
that also provide a tool like protoc.
