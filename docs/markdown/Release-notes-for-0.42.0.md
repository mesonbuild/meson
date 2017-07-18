---
title: Release 0.42
short-description: Release notes for 0.42 (preliminary)
...

**Preliminary, 0.42.0 has not been released yet.**

# New features

## Distribution tarballs from Mercurial repositories

Creating distribution tarballs can now be made out of projects based on
Mercurial. As before, this remains possible only with the Ninja backend.

## Keyword argument verification

Meson will now check the keyword arguments used when calling any function
and print a warning if any of the keyword arguments is not known. In the
future this will become a hard error.

## Add support for Genie to Vala compiler

The Vala compiler has an alternative syntax, Genie, that uses the `.gs`
file extension. Meson now recognises and uses Genie files.

## Pkgconfig support for additional cflags

The Pkgconfig module object can add arbitrary extra cflags to the Cflags
value in the .pc file, using the "extra_cflags" keyword:
```meson
pkg.generate(libraries : libs,
             subdirs : h,
             version : '1.0',
             name : 'libsimple',
             filebase : 'simple',
             description : 'A simple demo library.',
             extra_cflags : '-Dfoo' )
```

## Base options accessible via get_option()

Base options are now accessible via the get_option() function.
```meson
uses_lto = get_option('b_lto')
```

## Allow crate type configuration for Rust compiler

Rust targets now take an optional `rust_crate_type` keyword, allowing
you to set the crate type of the resulting artifact. Valid crate types
are `dylib` or `cdylib` for shared libraries, and `rlib` or
`staticlib` for static libraries. For more, see
Rust's [linkage reference][rust-linkage].

[rust-linkage]: https://doc.rust-lang.org/reference/linkage.html

## Simultaneous use of Address- and Undefined Behavior Sanitizers

Both the address- and undefined behavior sanitizers can now be used
simultaneously by passing `-Db_sanitize=address,undefined` to Meson.

## Unstable SIMD module

A new experimental module to compile code with many different SIMD
instruction sets and selecting the best one at runtime. This module
is unstable, meaning its API is subject to change in later releases.
It might also be removed altogether.
