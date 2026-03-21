#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
from dataclasses import dataclass
import os

from mesonbuild.mesonlib import File
from mesonbuild import build
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance


def _add_file_to_group(
        new_file: File,
        project_instance: ConvertProjectInstance,
        current_subdir: T.Optional[str],
        current_paths: T.List[str]) -> T.Tuple[str, T.List[str]]:  # fmt: skip
    normalized_path = project_instance.normalize_file_path(
        new_file.fname, new_file.subdir
    )
    old_subdir = current_subdir
    if current_subdir is not None:
        new_subdir = os.path.commonpath([current_subdir, normalized_path])
    else:
        new_subdir = normalized_path

    new_paths = list(current_paths)
    if old_subdir != new_subdir:
        rebased_paths = []
        if old_subdir is not None:
            for path in new_paths:
                abs_path = os.path.join(old_subdir, path)
                rebased_paths.append(os.path.relpath(abs_path, new_subdir))
        new_paths = rebased_paths

    full_path = os.path.join(normalized_path, os.path.basename(new_file.fname))
    new_paths.append(os.path.relpath(full_path, new_subdir))
    return new_subdir, new_paths


def determine_filegroup_name(source: str) -> str:
    root, ext = os.path.splitext(source)
    name = os.path.basename(root) + "_" + ext[1:]
    return name


@dataclass
class ConvertDep:
    target: str
    subdir: str = ""
    repo: str = ""
    source_url: str = ""
    source_filename: str = ""
    source_hash: str = ""

    def __hash__(self) -> int:
        return hash(self.target)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConvertDep):
            return False
        return self.target == other.target


@dataclass
class ConvertSrc:
    source: str
    target_dep: T.Optional[ConvertDep] = None

    @staticmethod
    def from_target(target_name: str, target_subdir: str) -> ConvertSrc:
        return ConvertSrc("", ConvertDep(target_name, target_subdir))

    def target_only(self) -> str:
        if self.target_dep:
            return self.target_dep.target
        else:
            return self.source

    def __hash__(self) -> int:
        if self.target_dep:
            return hash(self.target_dep)
        else:
            return hash(self.source)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConvertSrc):
            return False
        return self.source == other.source and self.target_dep == other.target_dep


class ConvertSrcList:
    """Helper to deduplicate ConvertSrc and normalize paths"""

    def __init__(self) -> None:
        self.srcs: T.Dict[str, ConvertSrc] = {}

    def add(self, src: ConvertSrc) -> None:
        key: str = ""

        if src.target_dep:
            key = src.target_dep.target
        else:
            key = src.source

        if src.target_dep and key in self.srcs:
            existing = self.srcs[key]
            existing.target_dep.subdir = os.path.commonpath(
                [existing.target_dep.subdir, src.target_dep.subdir]
            )
        else:
            self.srcs[key] = src

    def get_sources(self) -> T.List[ConvertSrc]:
        return list(self.srcs.values())


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

    def __init__(self, name: T.Optional[str] = None) -> None:
        self.subdir: T.Optional[str] = None
        self.paths: T.Set[str] = set()
        self.name = name

    def add_include_dir(
        self,
        include_dir: build.IncludeDirs,
        project_instance: ConvertProjectInstance,
    ) -> None:
        self.subdir = include_dir.curdir
        normalized_paths: T.List[str] = []
        for directory in include_dir.incdirs:
            normalized_paths.append(
                project_instance.normalize_path(directory, self.subdir)
            )

        for path in self.paths:
            if path == ".":
                path = ""
            normalized_paths.append(self.subdir + path)

        self.subdir = os.path.commonpath(normalized_paths)
        for normalized_path in normalized_paths:
            self.paths.add(os.path.relpath(normalized_path, self.subdir))

        if self.name is None:
            self.name = "inc_" + self.subdir.replace("/", "_")

    def add_header_file(
        self, file: File, project_instance: ConvertProjectInstance
    ) -> None:
        self.subdir, paths = _add_file_to_group(
            file, project_instance, self.subdir, list(self.paths)
        )
        self.paths = set()
        for path in paths:
            if path.endswith(".h") or path.endswith(".hpp"):
                newpath = os.path.dirname(path)
                if not newpath:
                    newpath = "."

                self.paths.add(newpath)
            else:
                self.paths.add(path)


class ConvertInstanceFileGroup:
    """A set of files with associated metadata.  Translates to Soong/Bazel filegroup module"""

    def __init__(self, name: T.Optional[str] = None) -> None:
        self.name = name
        self.subdir: T.Optional[str] = None
        self.srcs: T.List[str] = []

    def add_source_file(
        self, file: File, project_instance: ConvertProjectInstance
    ) -> None:
        self.subdir, self.srcs = _add_file_to_group(
            file, project_instance, self.subdir, self.srcs
        )
        if self.name is None:
            self.name = determine_filegroup_name(self.srcs[0])
