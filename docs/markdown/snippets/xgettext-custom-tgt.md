## `i18n.xgettext` now accepts CustomTarget and CustomTargetIndex as sources

Previously, [[@custom_tgt]] were accepted but silently ignored, and
[[@custom_idx]] were not accepted.

Now, they both can be used, and the generated outputs will be scanned to extract
translation strings.
