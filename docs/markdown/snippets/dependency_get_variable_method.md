## Dependency objects now have a get_variable method

This is a generic replacement for type specific variable getters such as
`ConfigToolDependency.get_configtool_variable` and
`PkgConfigDependency.get_pkgconfig_variable`, and is the only way to query
such variables from cmake dependencies.

This method allows you to get variables without knowing the kind of
dependency you have.

```meson
dep = dependency('could_be_cmake_or_pkgconfig')
# cmake returns 'YES', pkg-config returns 'ON'
if ['YES', 'ON'].contains(dep.get_variable(pkg-config : 'var-name', cmake : 'COP_VAR_NAME', default : 'NO'))
  error('Cannot build your project when dep is built with var-name support')
endif
```
