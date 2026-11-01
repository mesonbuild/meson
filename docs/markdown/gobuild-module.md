# Unstable IceStorm module

This module is available since version 1.6.0.

**Note**: this module is unstable. It is only provided as a technology
preview. Its API may change in arbitrary ways between releases or it
might be removed from Meson altogether.

## Usage

This module provides an experimental method to create a standalone Go executable
using the [Gobuild](https://pkg.go.dev/github.com/mjl-/gobuild) and
[CGO](https://pkg.go.dev/cmd/cgo) suite of tools.

The module exposes only one method called `project`, and it is used
like this:

```meson
# path/to/go.mod/folder/meson.build

gobuild = import('gobuild')
main_exe = gobuild.project('proj_name',
    <exhausive list of go files>,
    <exhausive list of embed.FS depdenencies>,
    include_directories: hello_world_inc,
    link_with: hello_world_lib,

    # true if `go mod tidy`, otherwise `go mod verify`
    gomod_tidy: true,

    # false if the meson project is setup with `--cross-file=...`
    native: false,
)

test('main cli app', main_exe)
```

The input to this function is the set of Go files and all other static files to
be embedded by [go embed](https://pkg.go.dev/embed). This produces a single
executable called `proj_name.exe`, potentially dynamically linked to
`hello_world.dll` if `hello_world_lib` emits a shared library.

In addition, it creates a ~test target~ run target `go test proj_name` for
running the unit-tests recursively in the go project.