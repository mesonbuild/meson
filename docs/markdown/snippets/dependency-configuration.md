## Dub configurations specification

The `dependency` function accepts a new keyword argument: `configuration`.
This keyword is used with `method: 'dub'`, to specify the configuration or
sub-configuration of a DUB's package.

```meson
vibe_http_dep = dependency('vibe-d:http',
    method: 'dub',
    configuration: 'vibe-d:tls/notls',
)
```
