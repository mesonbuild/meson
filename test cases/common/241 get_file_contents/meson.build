project(
  'meson-read-file',
  [],
  version: meson.read_file('VERSION').strip(),
)

assert(
  meson.project_version().version_compare('== 1.2.0'),
  'version was not read correctly'
)

expected = (
  '∮ E⋅da = Q,  n → ∞, ∑ f(i) = ∏ g(i), ∀x∈ℝ: ⌈x⌉ = −⌊−x⌋, α ∧ ¬β = ¬(¬α ∨ β)'
)
assert(
  meson.read_file('utf-16-text', encoding: 'utf-16').strip() == expected,
  'file was not decoded correctly'
)

# Make sure we handle `files()` objects properly, too
version_file = files('VERSION')

subdir('other')
