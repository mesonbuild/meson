## Updated default options are now used on reconfigure

Updating `project(..., default_options: ['option=new-value'])` used to have no
effect on reconfigure, unless `--wipe` was used. The reason was Meson does not
want a new default value to override a user defined value from command line.
Similar situation was happening when changing environment variables.

Meson now keeps track from where an option value has been defined and correctly
update the value if old value was not from a higher priority source.

The priority order is as follow:
- Unset: Value from Meson or from `meson_options.txt`.
- Default: Value from `default_options` keyword argument.
- Environment.
- Cross or native machine file.
- Command line: `-D` argument.
