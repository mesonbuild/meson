**new for Meson 0.52**

## get_option() type `path`

Meson can now take user option type `path` in meson_options.txt.
The path is expanded by Python pathlib.Path().expanduser() inside Meson.
Environment variables must not be specified in meson_options.txt
as the environment variables are treated as a plain string and will
most likely fail.

**examples**

in meson_options.txt

```meson
option('path_opt', type : 'path', value : '~/foo')
```

this will be available in meson.build like

```meson
mypath = get_option('path_opt')
```

where mypath will be a string with value like `c:\users\susan\foo` or
`/home/bill/foo` according to the user system type.
Note for cross builds, the `~` path expansion takes place on the host
machine.
This path need not exist beforehand.


**Example of what *not* to do**

in meson_options.txt

```meson
option('path_opt', type : 'path', value : '$HOME/foo')
```

Don't do that, because according to the example above, mypath == `$HOME/foo`,
which would normally not be wanted. Different shells have distinct
syntax for environment variables, which are not handled here.

Shell environment variable expansion like `-Dpath_opt=$HOME/foo` doesn't
always happen and is governed by your shell and so is not recommended in
general.
