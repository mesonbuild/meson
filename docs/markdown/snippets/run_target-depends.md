## `run_target` can now be used as a dependency

A `run_target()` can now be saved in a variable and reused as a dependency in
an `alias_target()`. This can be used to create custom alias rules that ensure
multiple other targets are run, even if those targets don't produce output
files.

For example:

```
i18n = import('i18n')

all_pot_targets = []

foo_i18n = i18n.gettext('foo')

all_pot_targets += foo_i18n[1]

alias_target('all-pot', all_pot_targets)
```
