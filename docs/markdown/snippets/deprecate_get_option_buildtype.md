## `get_option('buildtype')` is deprecated by `optimization` and `debug`

Build files have been doing anti-patterns such as checking whether debugging is
enabled with `get_option('buildtype').startswith('debug')`. This has been
incorrect *[since 0.48]* where we added separate options for `-Doptimization`
(choice) and `-Ddebug` (boolean) which also set `buildtype` for
backward-compatibility.

However, many [combinations of these two options](Builtin-options.html#build-type-options)
such as `-Doptimization=g -Ddebug=true` actually set **`buildtype='custom'`**.

The correct way to check for debugging is to simply do `get_option('debug')`.
For checking whether a 'release' build is being done, you can do something like:

```
if not get_option('debug') and get_option('optimization') == '3'
    message('Doing a release build')
fi
```

Depending on why you're checking for that, you may want to do something like:

```
if not get_option('debug') and get_option('optimization') not in ['s', '2', '3']
    message('Doing a release build')
fi
```

**Note:** Passing `--buildtype` or `-Dbuildtype` using the command-line, in
native/cross files, or in `project()` `default_options:` is still allowed as
a convenient short-cut. Note that (*[since 0.48]*), Meson has been [automatically
setting `-Doptimization` and `-Ddebug` using `-Dbuildtype` and
vice-versa](Builtin-options.html#build-type-options).

[since 0.48]: https://mesonbuild.com/Release-notes-for-0-48-0.html#toggles-for-build-type-optimization-and-vcrt-type
