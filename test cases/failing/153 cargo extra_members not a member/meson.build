project('cargo extra_members not a member')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojects')
endif

# fails because dep2 is never mentioned in a conditional target dependency
cargo = import('rust').workspace(extra_members: ['dep2'])
