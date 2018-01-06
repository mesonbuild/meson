## Added new partial_dependency method to dependencies and libraries

It is now possible to use only part of a dependency in a target. This allows,
for example, to only use headers with convenience libraries to avoid linking
to the same library multiple times.

```meson

dep = dependency('xcb')

helper = static_library(
  'helper',
  ['helper1.c', 'helper2.c'],
  dependencies : dep.partial_dependency(includes : true),
]

final = shared_library(
  'final',
  ['final.c'],
  dependencyes : dep,
)
```

A partial dependency will have the same name version as the full dependency it
is derived from, as well as any values requested.
