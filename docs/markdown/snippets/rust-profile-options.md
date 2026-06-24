## New Rust compiler options matching Cargo profile keys

Several new per-machine Rust compiler options have been added so that the
settings found in a Cargo `[profile]` section can be expressed natively:

- `rust_panic` (`none`, `unwind`, `abort`): selects the panic strategy
  (`-C panic=`).  It is ignored for `dylib` and `proc-macro` crates, which must
  always unwind.
- `rust_overflow_checks` (`true`, `false`): toggles runtime integer overflow
  checks (`-C overflow-checks=`).
- `rust_codegen_units` (integer, `0` to use the compiler default): number of
  code generation units to split a crate into (`-C codegen-units=`).
- `rust_incremental` (`true`, `false`): enables incremental compilation
  (`-C incremental=`).
- `rust_incremental_cache_dir` (path): directory used to store the incremental
  compilation data.  When left empty a per-target directory under the build
  directory is used.

The remaining Cargo profile keys map onto existing built-in options:
`opt-level` to `optimization`, `debug` to `debug`, `debug-assertions`
to `b_ndebug` and `lto` to `b_lto`.

The Cargo workspace object will also add these automatically based on
the value of another new option, `rust_cargo_profile`.
