## Windows.compile_resources CustomTarget

Previously the Windows module only accepted CustomTargets with one output, it
now accepts them with more than one output, and creates a windows resource
target for each output. Additionally it now accepts indexes of CustomTargets

```meson

ct = custom_target(
  'multiple',
  output : ['resource', 'another resource'],
  ...
)

ct2 = custom_target(
  'slice',
  output : ['resource', 'not a resource'],
  ...
)

resources = windows.compile_resources(ct, ct2[0])
```
