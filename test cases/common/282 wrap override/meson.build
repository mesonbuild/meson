project('wrap override')


subproject('sub')

# sub has subsub.wrap that provides subsub-1.0 dependency. Even if sub itself
# does not use it, that dependency should now be available.
dependency('subsub-1.0')
