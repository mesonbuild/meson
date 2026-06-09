project('native subproject introspect', 'c')

# The same subproject is configured for both the build machine (native : true)
# and the host machine (native : false). In a cross build these are two
# distinct configurations, so the library target it defines is introspected
# twice: with the same name but a different id.
subproject('recursive-both', native : true)
subproject('recursive-both', native : false)
