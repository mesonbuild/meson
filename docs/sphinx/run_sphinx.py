#!/usr/bin/env python3
import shutil
import subprocess
import sys
import pathlib
import tempfile


def main() -> None:
    sphinx_build, conf_dir, source_dir, gen_dir, output_dir, stamp_file = sys.argv[1:]

    with tempfile.TemporaryDirectory() as staging:
        # Static markdown sources go in first …
        shutil.copytree(source_dir, staging, dirs_exist_ok=True)
        # … then generated .md files overwrite / extend the staging tree.
        for md_file in pathlib.Path(gen_dir).glob('*.md'):
            shutil.copy2(md_file, staging)

        subprocess.run(
            [sphinx_build, '-b', 'html', '-c', conf_dir, staging, output_dir],
            check=True,
        )

    pathlib.Path(stamp_file).touch()


if __name__ == '__main__':
    main()
