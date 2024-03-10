#!/usr/bin/env python3

import argparse
import os
import textwrap


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('outdir')
    args = parser.parse_args()

    with open(os.path.join(args.outdir, 'generated.rs'), 'w') as f:
        f.write(textwrap.dedent('''\
            fn generated() {
                std::process::exit(0);
            }'''))


if __name__ == '__main__':
    main()
