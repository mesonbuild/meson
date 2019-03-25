## n_debug=if-release and buildtype=plain means no asserts

Previously if this combination was used then assertions were enabled,
which is fairly surprising behavior.
