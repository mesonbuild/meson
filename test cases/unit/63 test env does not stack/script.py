#!/usr/bin/env python3

import os

for name in ('append', 'prepend', 'set'):
    envname = 'TEST_VAR_' + name.upper()
    value = 'another-value-' + name
    envvalue = os.environ[envname]
    assert (envvalue == value), (name, envvalue)
