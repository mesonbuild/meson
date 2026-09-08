#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

# Hack to make relative imports to mlog possible
import sys
from pathlib import Path

root = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(root))

# Now run the actual code
from refman.main import main  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(main())
