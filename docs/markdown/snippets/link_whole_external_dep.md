## Allow as_link_whole() on external dependencies

It returns a copy of the dependency object with `*.a` arguments replaced with
the list of `.o` files they contain. This allows to merge together two static
libraries.
