## Added follow_symlinks arg to install_data, install_header, and install_subdir

The [[install_data]], [[install_headers]], [[install_subdir]] functions now
have an optional argument `follow_symlinks` that, if set to `true`, makes it so
symbolic links in the source are followed, rather than copied into the
destination tree, to match the old behavior.  The default, which is currently
to follow links, is subject to change in the future.
