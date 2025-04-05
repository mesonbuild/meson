#!/usr/bin/env python3
import json
import sys

if __name__ == '__main__':
    with open(sys.argv[1]) as fp:
        data = json.load(fp)

    assert 'include_directories' in data

    with open(sys.argv[2], 'w') as fp:
        fp.write("OK")
