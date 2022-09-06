## python.find_installation() now accepts pure argument

The default value of `pure:` for `py.install_sources()` and
`py.get_install_dir()` can now be changed by explicitly passing a `pure:` kwarg
to `find_installation()`.

This can be used to ensure that multiple `install_sources()` invocations do not
forget to specify the kwarg each time.
