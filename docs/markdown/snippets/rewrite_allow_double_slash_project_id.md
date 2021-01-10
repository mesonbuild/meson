## `//` is now allowed as a function id for `meson rewrite`.

msys bash may expand `/` to a path, breaking
`meson rewrite kwargs set project / ...`. Passing `//` will be converted to
`/` by msys bash but in order to keep usage shell-agnostic, also allow `//`
as the id such that `meson rewrite kwargs set project // ...` will work in
both msys bash and other shells.
