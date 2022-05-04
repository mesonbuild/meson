## Add `FeatureOption.force` to force a feature to enabled or disabled

Sometimes we want to force a feature to be enabled or disabled, take for example
when a feature should be automatically turned off for one platform, but off for
another:

```meson
feat = get_option('feat')
if feat.auto()
  feat = feat.enable_auto_if(host_machine.system() == 'windows) \
             .disable_auto_if(host_machine.system() != 'windows)
endif
```
which could simply be:
```meson
feat = get_option('feat').force(host_machine.system() == 'windows')
```
