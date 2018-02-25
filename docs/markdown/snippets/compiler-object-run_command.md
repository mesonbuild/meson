## Compiler object can now be passed to run_command()

This can be used to run the current compiler with the specified arguments
to obtain additional information from it.
One of the use cases is to get the location of development files for the
GCC plugins:

    cc = meson.get_compiler('c')
    result = run_command(cc, '-print-file-name=plugin')
    plugin_dev_path = result.stdout().strip()
