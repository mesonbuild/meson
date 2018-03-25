## test now supports depends keyword parameter

Build targets and custom targets can be listed in depends argument of test
function. These targets will be built before test is run even if they have
`build_by_default : false`.
