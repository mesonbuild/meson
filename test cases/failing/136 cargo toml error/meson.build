project('cargo-toml-error', 'c')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojets')
endif

# Check if we have tomllib/tomli (not toml2json)
python = find_program('python3', 'python')
result = run_command(python, '-c', 'import tomllib', check: false)
if result.returncode() != 0
  result = run_command(python, '-c', 'import tomli', check: false)
  if result.returncode() != 0
    # Skip test if using toml2json - error format will be different
    error('MESON_SKIP_TEST toml2json in use, skipping test')
  endif
endif

# This should trigger a CargoTomlError with proper location info
foo_dep = dependency('foo-0')
