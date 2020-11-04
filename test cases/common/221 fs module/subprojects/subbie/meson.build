project('subbie')

fs = import('fs')

assert(fs.exists('subprojectfile.txt'), 'Subproject root file not found.')
assert(fs.is_samepath(meson.project_source_root(), meson.current_source_dir()), 'is_samepath not detecting same directory')
assert(fs.is_samepath(meson.project_build_root(), meson.current_build_dir()), 'is_samepath not detecting same directory')

# We cannot assert anything on the result of this, but we can at least
# check that it doesn't fail
fs.expandglob('~/*')

assert(fs.expandglob('sub*') == ['subprojectfile.txt', 'subsub'],
       'Incorrect glob for sub*.')
assert(fs.expandglob('sub*', '*.txt') == ['subprojectfile.txt', 'subsub'],
       'Duplicates not removed correctly.')
assert(fs.expandglob('nonex*') == [], 'Nonexistent file not dropped.')
assert(fs.expandglob('nonexistent') == [], 'Nonexistent file not dropped.')
if build_machine.system() == 'windows'
  assert(fs.expandglob('**/sub*') == ['subprojectfile.txt', 'subsub', 'subsub\subsubfile.txt'],
         'Incorrect glob for **/sub*.')
  assert(fs.expandglob('**/sub*') == ['subprojectfile.txt', 'subsub', 'subsub\subsubfile.txt'],
         'Incorrect glob for **/sub*.')
else
  assert(fs.expandglob('../*') == ['../subbie'],
         'Incorrect glob for ../*.')
  assert(fs.expandglob('**/sub*') == ['subprojectfile.txt', 'subsub', 'subsub/subsubfile.txt'],
         'Incorrect glob for **/sub*.')
endif

# Hack around unsafe array limitations
install_data(fs.expandglob('*.txt')[0])

subdir('subsub')
