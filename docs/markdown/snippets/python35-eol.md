## Python 3.5 support will be dropped in the next release

The final [Python 3.5 release was 3.5.10 in September](https://www.python.org/dev/peps/pep-0478/#id4).
This release series is now End-of-Life (EOL). The only LTS distribution that
still only ships Python 3.5 is Ubuntu 16.04, which will be
[EOL in April 2021](https://ubuntu.com/about/release-cycle).

Python 3.6 has numerous features that we find useful such as improved support
for the `typing` module, f-string support, and better integration with the
`pathlib` module.

As a result, we will begin requiring Python 3.6 or newer in Meson 0.57, which
is the next release. Starting with Meson 0.56, we now print a `NOTICE:` when
a `meson` command is run on Python 3.5 to inform users about this. This notice
has also been backported into the 0.55.2 stable release.
