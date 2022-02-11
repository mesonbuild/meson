## pkgconfig.generate will now include variables for builtin directories when referenced

When using the `variables:` family of kwargs to `pkgconfig.generate` to refer
to installed paths, traditionally only `prefix`, `includedir`, and `libdir`
were available by default, and generating a correct (relocatable) pkg-config
file required manually constructing variables for e.g. `datadir`.

Meson now checks each variable to see if it begins with a reference to a
standard directory, and if so, adds it to the list of directories for which a
builtin variable is created.

For example, before it was necessary to do this:
```meson
pkgconfig.generate(
    name: 'bash-completion',
    description: 'programmable completion for the bash shell',
    dataonly: true,
    variables: {
        'prefix': get_option('prefix'),
        'datadir': join_paths('${prefix}', get_option('datadir')),
        'sysconfdir': join_paths('${prefix}', get_option('sysconfdir')),

        'compatdir': '${sysconfdir}/bash_completion.d',
        'completionsdir': '${datadir}/bash-completion/completions',
        'helpersdir': '${datadir}/bash-completion/helpers',
    },
    install_dir: join_paths(get_option('datadir'), 'pkgconfig'),
)
```

Now the first three variables are not needed.
