## `--cap-lints allow` used for Cargo subprojects

Similar to Cargo itself, all downloaded Cargo subprojects automatically
add the `--cap-lints allow` compiler argument, thus hiding any warnings
from the compiler.

Related to this, `warning_level=0` now translates into `--cap-lints allow`
for Rust targets instead of `-A warnings`.
