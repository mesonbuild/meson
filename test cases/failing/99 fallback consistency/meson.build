project('proj', 'c')

# Subproject overrides 'sub' with another variable than dep2. This should fail.
dependency('sub', fallback : ['sub', 'dep2'])
