project('cargo extra_members not a member')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojects')
endif

# Compare to failing/153 - dep2 is part of the packages because
# dep depends on it, but you cannot specify it directly because
# it is only an indirect dependency of workspace members.
cargo = import('rust').workspace(extra_members: ['dep'])
assert('dep' in cargo.packages())
assert('dep2' in cargo.packages())
