## Wrap files can contain a list of patch files to apply

A list of local patch files can be provided by the `.wrap` file and they will be
applied after the subproject has been extracted or cloned from git. This requires
the `patch` or `git` command-line tool.

```ini
[wrap-file]
directory = libfoobar-1.0

source_url = https://example.com/foobar-1.0.tar.gz
source_filename = foobar-1.0.tar.gz
source_hash = 5ebeea0dfb75d090ea0e7ff84799b2a7a1550db3fe61eb5f6f61c2e971e57663

[patch-files]
strip = 1
patches = ['0001.patch', '0002.patch']
```
