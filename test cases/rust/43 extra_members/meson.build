project('rust ws extra_members', 'rust',
    meson_version: '>= 1.11'
)

cargo = import('rust').workspace(extra_members: ['subdir/alpha'])

if 'beta' in cargo.packages()
    error('Unexpectedly resolved glob member')
endif

cargo.package('alpha').executable()
cargo.package('gamma').executable()
