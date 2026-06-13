#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from dataclasses import dataclass
import os

from mesonbuild.mesonlib import File


def include_dir_name(subdir: str) -> str:
    return 'inc_' + subdir.replace('/', '_')


@dataclass
class ConvertId:
    """Data class holding everything you need to know about a module (library,
       tool, custom_target, filegroup) or a local file

    - name (required)
    - subdir (not required) (could be in external repo)
    - external repo (not required)
    - source_url, source_filename, source_hash (not required, download info)"""

    name: str
    subdir: str = ''
    repo: str = ''
    source_url: str = ''
    source_filename: str = ''
    source_hash: str = ''
    local: bool = False

    @staticmethod
    def from_local_file(file: File) -> ConvertId:
        return ConvertId(file.fname, file.subdir, local=True)

    @staticmethod
    def from_local_name(name: str, subdir: str = '') -> ConvertId:
        return ConvertId(name, subdir, local=True)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConvertId):
            return False
        return self.name == other.name


class ConvertInstanceFlag:
    """Holds things like c_flags, cpp_flags, link_flags that can be applied to a target"""

    def __init__(self, name: str, subdir: str, language: str):
        self.name = name
        self.subdir = subdir
        self.language = language
        self.project_native_args = False
        self.compile_args: T.List[str] = []
        self.link_args: T.List[str] = []

    def add_compile_arg(self, arg: str) -> None:
        self.compile_args.append(arg.replace('"', '\\"'))
        self.compile_args.sort()

    def add_link_arg(self, arg: str) -> None:
        self.link_args.append(arg.replace('"', '\\"'))
        self.link_args.sort()


class ConvertInstanceIncludeDirectory:
    """Representation of build.IncludeDirs, optimized for the convert operation"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.subdir = ''
        self.paths: T.Set[str] = set()

    @staticmethod
    def from_subdir(subdir: str) -> ConvertInstanceIncludeDirectory:
        name = include_dir_name(subdir)
        directory = ConvertInstanceIncludeDirectory(name)
        directory.paths.add('.')
        directory.subdir = subdir
        return directory

    def add_new_paths(self, new_paths: T.Set[str]) -> None:
        # Add current paths to new_paths
        if self.subdir:
            for path in self.paths:
                if path == '.':
                    new_paths.add(self.subdir)
                else:
                    new_paths.add(os.path.join(self.subdir, path))

        # Re-normalize to new subdir
        self.subdir = os.path.commonpath(list(new_paths))
        self.paths = set()
        for path in new_paths:
            self.paths.add(os.path.relpath(path, self.subdir))


class ConvertInstanceFileGroup:
    """A set of files with associated metadata.  Translates to Soong/Bazel filegroup module"""

    def __init__(self, name: str, subdir: str) -> None:
        self.name = name
        self.subdir = subdir
        self.srcs: T.Set[str] = set()

    def add_source_file(self, file: File) -> None:
        self.srcs.add(os.path.basename(file.fname))


class ConvertInstancePythonTarget:
    def __init__(self, name: str, subdir: str) -> None:
        self.name = name
        self.subdir = subdir
        self.srcs: T.Set[ConvertId] = set()
        self.libs: T.Set[ConvertId] = set()

    def add_source(self, src: ConvertId) -> None:
        self.srcs.add(src)

    def add_libs(self, dep: ConvertId) -> None:
        self.libs.add(dep)


class ConvertInstancePythonBinary(ConvertInstancePythonTarget):
    def __init__(self, name: str, subdir: str, main: str):
        super().__init__(name, subdir)
        self.main = main
