## Introduce dataonly for the pkgconfig module
This allows users to disable writing out the inbuilt variables to
the pkg-config file as they might actualy not be required.

One reason to have this is for architecture-independent pkg-config
files in projects which also have architecture-dependent outputs.

```
pkgg.generate(
  name : 'libhello_nolib',
  description : 'A minimalistic pkgconfig file.',
  version : libver,
  dataonly: true
)
```
