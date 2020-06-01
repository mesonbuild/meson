# Wrap maintainer tools

The [mesonwrap repository](https://github.com/mesonbuild/mesonwrap) provides tools
to maintain the WrapDB. Read-only features such can be used by anyone without Meson admin rights.

## Personal access token

Some tools require access to the Github API.
A [personal access token](https://github.com/settings/tokens) may be required
if the freebie Github API quota is exhausted. `public_repo` scope is required
for write operations.

```
$ cat ~/.config/mesonwrap.ini
[mesonwrap]
github_token = <github token>
```
