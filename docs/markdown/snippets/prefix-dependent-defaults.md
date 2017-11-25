# Prefix-dependent defaults for sysconfdir, localstatedir and sharedstatedir

These options now default in a way consistent with
[FHS](http://refspecs.linuxfoundation.org/fhs.shtml) and common usage.

If prefix is `/usr`, default sysconfdir to `/etc`, localstatedir to `/var` and
sharedstatedir to `/var/lib`.

If prefix is `/usr/local` (the default), default localstatedir to `/var/local`
and sharedstatedir to `/var/local/lib`.
