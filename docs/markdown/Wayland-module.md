# Unstable Wayland Module

This module is available since version 0.62.0.

This module provides helper functions to find wayland protocol
xmls and to generate .c and .h files using wayland-scanner

**Note**: this module is unstable. It is only provided as a technology
preview. Its API may change in arbitrary ways between releases or it
might be removed from Meson altogether.

## Quick Usage

```meson
project('hello-wayland', 'c')

wl_dep = dependency('wayland-client')
wl_mod = import('unstable-wayland')

xml = wl_mod.find_protocol('xdg-shell')
xdg_shell = wl_mod.scan_xml(xml)

executable('hw', 'main.c', xdg_shell, dependencies : wl_dep)
```

## Methods

### find_protocol

```meson
xml = wl_mod.find_protocol(
  'xdg-decoration',
  state : 'unstable',
  version : 1,
)
```
This function requires one positional argument: the protocol base name.
- `state` Optional arg that specifies the current state of the protocol.
Either stable, staging, or unstable.
The default is stable.
- `version` The backwards incompatible version number.
Required for staging or unstable. An error is raised for stable.

### scan_xml
```meson
generated = wl_mod.scan_xml(
  'my-protocol.xml',
  side : 'client',
  scope : 'private',
)
```
This function accepts one or more arguments of either string or file type.

- `side` Optional arg that specifies if client or server side code is generated.
The default is client side.
- `scope` Optional arg that specifies the scope of the generated code.
Either public or private.
The default is private.


## Links
- [Official Wayland Documentation](https://wayland.freedesktop.org/docs/html/)
- [Wayland GitLab](https://gitlab.freedesktop.org/wayland)
- [Wayland Book](https://wayland-book.com/)
