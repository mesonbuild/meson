#!/usr/bin/env python3

import configparser
import sys

with open(sys.argv[2], 'w', encoding='utf-8') as outfile:
    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    for key, val in config["DEFAULT"].items():
        outfile.write(f"#define {key.upper()} {val}\n")
