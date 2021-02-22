## Specify man page locale during installation

Locale directories can now be passed to `install_man`:
    
```meson
# instead of
# install_data('foo.fr.1', install_dir: join_paths(get_option('mandir'), 'fr', 'man1'), rename: 'foo.1')`
install_man('foo.fr.1', locale: 'fr')
```
