## `introspect --projectinfo` can now be used without configured build directory

This allows IDE integration to get information about the project before the user has configured a build directory.

Before you could use `meson.py introspect --projectinfo build-directory`.
Now you also can use `meson.py introspect --projectinfo project-dir/meson.build`.

The output is similiar to the output with a build directory but additionally also includes information from `introspect --buildsystem-files`.

For example `meson.py introspect --projectinfo test\ cases/common/47\ subproject\ options/meson.build`
This outputs (pretty printed for readability):
```
{
    "buildsystem_files": [
        "meson_options.txt",
        "meson.build"
    ],
    "name": "suboptions",
    "version": null,
    "descriptive_name": "suboptions",
    "subprojects": [
        {
            "buildsystem_files": [
                "subprojects/subproject/meson_options.txt",
                "subprojects/subproject/meson.build"
            ],
            "name": "subproject",
            "version": "undefined",
            "descriptive_name": "subproject"
        }
    ]
}
```

Both usages now include a new `descriptive_name` property which always shows the name set in the project.
