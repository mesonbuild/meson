## Python 3.6 support will be dropped in the next release

The final [Python 3.6 release was 3.6.15 in September](https://www.python.org/dev/peps/pep-0494/#lifespan).
This release series is now End-of-Life (EOL). The only LTS distribution that
still ships Python 3.5 as the default Python is Ubuntu 18.04, which has Python
3.8 available as well.

Python 3.7 has various features that we find useful such as future annotations,
the importlib.resources module, and dataclasses.

As a result, we will begin requiring Python 3.7 or newer in Meson 0.62, which
is the next release. Starting with Meson 0.61, we now print a `NOTICE:` when
a `meson` command is run on Python 3.6 to inform users about this.
