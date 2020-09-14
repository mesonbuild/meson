## Machine file keys are stored case sensitive

Previous the keys were always lowered, which worked fine for the values that
were allowed in the machine files. With the addition of per-project options
we need to make these sensitive to case, as the options in meson_options.txt
are sensitive to case already.
