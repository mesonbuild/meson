## install_man: add support install_tag kwarg

By default install_man uses 'man' tag for its files which not always is desirable,
for example if project uses plugin functionality and plugin wants to install its own man files
it was not possible using `meson install --tags xxx`.
