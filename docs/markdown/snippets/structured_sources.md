## Structured sources for Rust

Rust is different than most languages supported by Meson because it relies
exclusively on the layout of the files on disk for importing them, and it
generates a single .o from those files. This means that if the on disk layout is
different than what rustc expects, such as with generated files, the compilation
will fail.

Structured sources then are a way to describe what the layout must look like on
disk. Meson can then generate rules to ensure that this layout exists.

Consider that you might generate a file from XML using a python script, then
want to compile use the output of that file as a rust module:

```
/
↳ main.rs
↳ /mymod
  ↳ mod.rs  # generated
```

Since meson puts all generated files in a build tree, it needs to copy the
generated md.rs into `builddir/mymod` for the Rust target to compile.

To make this work you can write this:

```meson
gen_mod = custom_target('mod.rs', ...)

exe = executable(
  'exe',
  {
    '': ['main.rs'],
    'mymod': [gen_mod]
  }
)
```

Meson will generate the rules for generating mod.rs, and ensure that the
directory structure with main.rs at the root, and mymod/mod.rs is created before
compiling main.rs.

Currently, only Rust supports this feature, and only when using the ninja backend.
