# Copyright 2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool.


"""Python backend

Implements PEP 517 hooks.
"""

from __future__ import annotations

import contextlib
import email.message
import functools
import gzip
import io
import json
import os
import os.path
import pathlib
import shutil
import tarfile
import tempfile
import typing

from typing import Any, Dict, Iterator, Optional, Union

from .. import mesonmain, mlog


PathLike = Union[str, os.PathLike]


@contextlib.contextmanager
def _cd(path: PathLike) -> Iterator[None]:
    """Context manager helper to change the current working directory -- cd."""
    old_cwd = os.getcwd()
    os.chdir(os.fspath(path))
    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextlib.contextmanager
def _edit_targz(path: PathLike) -> Iterator[tarfile.TarFile]:
    """Opens a .tar.gz file in memory for edition."""
    memory = io.BytesIO()
    with gzip.open(path) as compressed:
        memory.write(compressed.read())

    memory.seek(0)
    with tarfile.open(fileobj=memory, mode='a') as tar:
        yield tar

    memory.seek(0)
    with gzip.open(path, 'wb') as new_compressed:
        new_compressed.write(memory.read())  # type: ignore


class Project():
    """Meson project wrapper to generate Python artifacts."""

    def __init__(self, source_dir: PathLike, build_dir: PathLike) -> None:
        self._source_dir = pathlib.Path(source_dir)
        self._build_dir = pathlib.Path(build_dir)

        # make sure the build dir exists
        self._build_dir.mkdir(exist_ok=True)

        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        self._mtime = int(source_date_epoch) if source_date_epoch else None

        # configure the project
        self._meson('setup', os.fspath(source_dir), os.fspath(build_dir))

    def _meson(self, *args: str) -> None:
        print(mlog.cyan('+ meson {}'.format(' '.join(args))))
        with _cd(self._build_dir):
            mesonmain.run(args, mesonmain.__file__)  # type: ignore

    @classmethod
    @contextlib.contextmanager
    def with_temp_builddir(cls, source_dir: PathLike = os.path.curdir) -> Iterator[Project]:
        """Creates a project instance pointing to a temporary build directory."""
        with tempfile.TemporaryDirectory(prefix='meson-python-') as tmpdir:
            yield cls(os.path.abspath(source_dir), tmpdir)

    @functools.lru_cache()
    def _info(self, name: str) -> Dict[str, str]:
        """Read info from meson-info directory."""
        file = self._build_dir.joinpath('meson-info', f'{name}.json')
        return typing.cast(
            Dict[str, str],
            json.loads(file.read_text())
        )

    @property
    def name(self) -> str:
        """Project name."""
        return self._info('intro-projectinfo')['descriptive_name']

    @property
    def version(self) -> str:
        """Project version."""
        return self._info('intro-projectinfo')['version']

    @property
    def metadata(self) -> email.message.Message:
        """Project metadata."""
        metadata = email.message.Message()
        metadata['Metadata-Version'] = '2.1'
        metadata['Name'] = self.name
        metadata['Version'] = self.version
        # FIXME: add missing metadata
        return metadata

    def sdist(self, directory: PathLike) -> pathlib.Path:
        """Generates a sdist (source distribution) in the specified directory."""
        # generate meson dist file
        self._meson('dist', '--formats', 'gztar')

        # move meson dist file to output path
        dist_name = f'{self.name}-{self.version}'
        dist_filename = f'{dist_name}.tar.gz'
        meson_dist = pathlib.Path(self._build_dir, 'meson-dist', dist_filename)
        sdist = pathlib.Path(directory, dist_filename)
        shutil.move(meson_dist, sdist)

        # add PKG-INFO to dist file to make it a sdist
        metadata = self.metadata.as_bytes()
        with _edit_targz(sdist) as tar:
            info = tarfile.TarInfo(f'{dist_name}/PKG-INFO')
            info.size = len(metadata)
            with io.BytesIO(metadata) as data:
                tar.addfile(info, data)

        return sdist


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[Dict[Any, Any]] = None,
) -> str:
    mlog.setup_console()

    out = pathlib.Path(sdist_directory)
    with Project.with_temp_builddir() as project:
        return project.sdist(out).name


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Dict[Any, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    raise NotImplementedError
