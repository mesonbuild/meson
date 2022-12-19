## New `declare_dependency(objects: )` argument

A new argument to `declare_dependency` makes it possible to add objects
directly to executables that use an internal dependency, without going
for example through `link_whole`.
