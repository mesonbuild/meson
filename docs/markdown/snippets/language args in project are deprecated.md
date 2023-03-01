## Using language arguments in project(default_options) is deprecated

One can place any valid command line option in the `project(default_options)`
field. The problem is that some of these options result in very strange behavior.
Case an point is c_args (and friends), which will do the following when placed
in the project() options:

1. prevent $CFLAGS from being read
2. prevent the `c_args` from being read from a machine file (cross or native)
3. be replaced by any arguments passed via -Dc_args

2 Is especially problematic for OS and distro vendors, which often rely on
setting the compile args they want via $CFLAGS (and friends)

The reality is that most people don't want any of this behavior, and what they
really want is to use either `add_project_arguments()` or
`add_global_arguments()`.
