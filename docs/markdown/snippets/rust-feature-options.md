## cargo: Add global features options
- Add rust.add_cargo_features() method to add features from meson.build.
  It is similar to add_global_arguments(), we can add global cargo
  features until it is first used.
- Add rust.cargo_features and rust.cargo_no_default_features CLI options
  to allow the user to add extra features.
