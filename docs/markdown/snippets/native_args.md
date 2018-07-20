## Projects args can be set separately for cross and native builds (potentially breaking change)

It has been a longstanding bug (or let's call it a "delayed bug fix")
that if yodo this:

```meson
add_project_arguments('-DFOO', language : 'c')
```

Then the flag is used both in native and cross compilations. This is
very confusing and almost never what you want. To fix this a new
keyword `native` has been added to all functions that add arguments,
namely `add_global_arguments`, `add_global_link_arguments`,
`add_project_arguments` and `add_project_link_arguments` that behaves
like the following:

```
## Added to native builds when compiling natively and to cross
## compilations when doing cross compiles.
add_project_arguments(...)

## Added only to native compilations, not used in cross compilations.
add_project_arguments(..., native : true)

## Added only to corss compilations, not used in native compilations.
add_project_arguments(..., native : false)
```

Also remember that cross compilation is a property of each
target. There can be target that are compiled with the native compiler
and some which are compiled with the cross compiler.

Unfortunately this change is backwards incompatible and may cause some
projects to fail building. However this should be very rare in practice.
