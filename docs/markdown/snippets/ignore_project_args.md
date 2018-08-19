## ignore project arguments in some targets

All build targets now have `ignore_project_args` and `ignore_project_link_args`
keyword arguments. When set to `true` those targets won't be using flags passed
to `add_project_arguments()` or `add_project_link_arguments()`. This is useful
when some flags are needed by most targets but with a few exceptions.
