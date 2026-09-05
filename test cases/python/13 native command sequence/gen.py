import argparse

import codegen


parser = argparse.ArgumentParser()
parser.add_argument("output")
args = parser.parse_args()

with open(args.output, "w", encoding="utf-8") as f:
    f.write(codegen.get_c_code())
