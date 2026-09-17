project('unused Cargo patch', meson_version: '>= 1.13')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojects')
endif

# fails because patched is in [patches] but is unused
import('rust').workspace(extra_members: ['patched'])
