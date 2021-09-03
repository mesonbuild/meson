import argparse
import typing as T

from ..utils import ar

def run(args: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Only print file names')
    parser.add_argument('--outdir', default='.',
                        help='Directory where to extract archive')
    parser.add_argument('filename',
                        help='Path to static library')
    options = parser.parse_args(args)

    files = ar.extract(options.filename, options.outdir, options.dry_run)
    if options.dry_run:
        print('\n'.join(files))

    return 0
