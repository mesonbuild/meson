# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Marco Rebhan <me@dblsaiko.net>

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePath

from .envconfig import MachineInfo
from .mesonlib import File, MachineChoice

import typing as T

if T.TYPE_CHECKING:
    from .build import BuildTargetTypes, BundleTargetBase, StructuredSources


PlistDataType = T.Union[str, bool, T.List['PlistDataType'], T.Dict[str, 'PlistDataType']]

# https://developer.apple.com/library/archive/documentation/DeveloperTools/Reference/XcodeBuildSettingRef/1-Build_Setting_Reference/build_setting_ref.html
# https://developer.apple.com/documentation/xcode/build-settings-reference


class BundleLayout(Enum):
    """
    Names for these slightly named after their CoreFoundation names.
    'oldstyle' is bundles with the executable in the top directory and a Resources folder, as used in Framework bundles
    and GNUstep,
    'contents' is the standard macOS application bundle layout with everything under a Contents directory,
    'flat' is the iOS-style bundle with every file in the root directory of the bundle.
    """

    OLDSTYLE = 'oldstyle'
    FLAT = 'flat'
    CONTENTS = 'contents'


class BundleType(Enum):
    """
    Subset of Xcode "product types". Affect the bundle defaults.
    """

    APPLICATION = 'application'
    FRAMEWORK = 'framework'
    BUNDLE = 'bundle'


@dataclass(eq=False)
class BundleInfo:
    """
    Backend-agnostic bundle info.
    """

    # How exactly bundle paths etc. are realized depends on the target.
    owner: BundleTargetBase = field(repr=False, hash=False, compare=False)

    # Layout settings
    layout: T.Optional[BundleLayout] = None
    version: T.Optional[str] = None
    executable_folder_name: T.Optional[str] = None

    # Info.plist settings
    info_dict: T.Dict[str, PlistDataType] = field(default_factory=dict)
    info_dict_file: T.Optional[File] = None

    # Contents
    resources: T.Optional[StructuredSources] = None
    contents: T.Optional[StructuredSources] = None
    headers: T.Optional[StructuredSources] = None
    extra_binaries: T.List[BuildTargetTypes] = field(default_factory=list)

    def _m(self) -> MachineInfo:
        return self.owner.environment.machines[self.owner.for_machine]

    def _type(self) -> BundleType:
        return self.owner.get_bundle_type()

    def get_layout(self) -> BundleLayout:
        if self.layout is not None:
            return self.layout

        if self._type() == BundleType.FRAMEWORK:
            return BundleLayout.OLDSTYLE

        m = self._m()

        if m.is_darwin() and not m.is_macos():
            return BundleLayout.FLAT

        return BundleLayout.CONTENTS

    def get_version(self) -> T.Optional[str]:
        # Versioned bundles contain symlinks, don't build them on Windows
        if self.owner.environment.machines[MachineChoice.HOST].is_windows():
            return None

        # Only support frameworks as versioned bundles.
        if self._type() != BundleType.FRAMEWORK:
            return None

        if self.version is not None:
            version = self.version
        else:
            version = 'A'

        return version

    def get_configured_info_dict(self) -> T.Dict[str, PlistDataType]:
        """
        Returns Info.plist contents known at configure time (without the user-supplied Info.plist data merged)
        """

        d = {'CFBundleInfoDictionaryVersion': '6.0'}

        t = self._type()

        if t == BundleType.APPLICATION:
            m = self._m()

            if m.is_darwin() and not m.is_macos():
                principal_class = 'UIApplication'
            else:
                principal_class = 'NSApplication'

            d.update({
                'CFBundleExecutable': self.get_executable_name(),
                'CFBundlePackageType': 'APPL',
                'NSPrincipalClass': principal_class,
            })
        elif t == BundleType.FRAMEWORK:
            d.update({
                'CFBundleExecutable': self.get_executable_name(),
                'CFBundlePackageType': 'FMWK',
            })
        else:
            d.update({
                'CFBundlePackageType': 'BNDL',
            })

        d.update(self.info_dict)
        return d

    def get_paths_to_link_contents(self) -> T.List[PurePath]:
        version = self.get_version()

        if version is None:
            return []

        assert version != 'Current'

        return [
            PurePath(),
            PurePath() / 'Versions' / 'Current'
        ]

    def get_contents_folder_path(self) -> PurePath:
        p = PurePath()

        version = self.get_version()

        if version is not None:
            p = p / 'Versions' / version

        if self.get_layout() == BundleLayout.CONTENTS:
            p = p / 'Contents'

        return p

    def get_unlocalized_resources_folder_path(self) -> PurePath:
        contents = self.get_contents_folder_path()

        if self.get_layout() == BundleLayout.FLAT:
            return contents
        else:
            return contents / 'Resources'

    def get_executable_folder_name(self) -> str:
        if self.get_layout() != BundleLayout.CONTENTS:
            return ''

        if self.executable_folder_name is not None:
            return self.executable_folder_name

        m = self._m()

        # As in _CFBundleGetPlatformExecutablesSubdirectoryName (CoreFoundation)
        if m.is_darwin():
            return 'MacOS'
        elif m.is_windows():
            return 'Windows'
        elif m.is_sunos():
            return 'Solaris'
        elif m.is_cygwin():
            return 'Cygwin'
        elif m.is_linux():
            return 'Linux'
        elif m.is_freebsd():
            return 'FreeBSD'
        elif m.is_wasm():
            return 'WASI'
        else:
            return ''

    def get_executable_folder_path(self) -> PurePath:
        return self.get_contents_folder_path() / self.get_executable_folder_name()

    def get_executable_name(self) -> str:
        return self.owner.get_executable_name()

    def get_executable_path(self) -> PurePath:
        return self.get_executable_folder_path() / self.get_executable_name()

    def get_infoplist_path(self) -> PurePath:
        if self.get_layout() == BundleLayout.OLDSTYLE:
            return self.get_unlocalized_resources_folder_path()
        else:
            return self.get_contents_folder_path()

    def get_public_headers_folder_path(self) -> PurePath:
        return self.get_contents_folder_path() / 'Headers'

    def get_private_headers_folder_path(self) -> PurePath:
        return self.get_contents_folder_path() / 'PrivateHeaders'

    def get_modules_folder_path(self) -> PurePath:
        return self.get_contents_folder_path() / 'Modules'

    def get_wrapper_extension(self) -> str:
        t = self._type()

        if t == BundleType.APPLICATION:
            m = self._m()

            if m.is_darwin() and not m.is_macos():
                return 'ipa'
            else:
                return 'app'
        elif t == BundleType.FRAMEWORK:
            return 'framework'
        else:
            return 'bundle'

    def get_wrapper_name(self) -> str:
        return f'{self.owner.name}.{self.get_wrapper_extension()}'
