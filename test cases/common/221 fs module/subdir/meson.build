assert(fs.exists('subdirfile.txt'), 'Subdir file lookup is broken.')
assert(fs.is_samepath(meson.project_source_root(), '..'), 'is_samepath not detecting same directory')
assert(fs.is_samepath(meson.project_build_root(), meson.current_build_dir() / '..'), 'is_samepath not detecting same directory')
