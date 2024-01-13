## `depends` kwarg now supported by compiler.preprocess()

It is now possible to specify the dependent targets with `depends:`
for compiler.preprocess(). These targets should be built before the
preprocessing starts.
