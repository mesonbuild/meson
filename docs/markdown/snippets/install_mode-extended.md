## install_mode argument extended to all installable targets

It is now possible to pass an install_mode argument to all installable targets,
such as executable(), libraries, headers, man pages and custom/generated
targets.

The install_mode argument can be used to specify the file mode in symbolic
format and optionally the owner/uid and group/gid for the installed files.
