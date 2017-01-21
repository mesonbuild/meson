project('include order', 'c')

# Test that the order of priority of include paths (from first to last) is:
#
# 1. Target's current build directory
# 2. Target's current source directory
# 3. Include paths added with the `c_args:` kwarg
# 4. Include paths added with the `include_directories`: kwarg
#    Within this, the build dir takes precedence over the source dir
# 5. Include paths added via `include_directories:` of internal deps
#    Within this, the build dir takes precedence over the source dir

# Defines an internal dep
subdir('sub1')
# Defines a per-target include path
subdir('sub2')
# Directory for `c_args:` include path
subdir('sub3')
# The directory where the target resides
subdir('sub4')

test('eh', e)
