from __future__ import annotations

from . import vcxproj


from dataclasses import dataclass, field
from pathlib import Path
import re
import uuid
import typing as T


@dataclass(frozen=True)
class Configuration:

    name: str
    arch: str

    def __init__(self, config: str):
        name, arch = config.rsplit('|', maxsplit=1)
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'arch', arch)

    def __str__(self) -> str:
        return f'{self.name}|{self.arch}'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (Configuration, vcxproj.Configuration)):
            return self.name == other.name and self.arch == other.arch
        raise TypeError(f'{other!r} must be a Configuration object')

    def __lt__(self, other: Configuration) -> bool:
        return (self.name, self.arch) < (other.name, other.arch)


@dataclass
class ProjectData:

    uuid: str
    name: str
    path: Path

    configurations: set[Configuration] = field(default_factory=set)
    subdir: str | None = None
    build_solution_target: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.subdir, str):
            self.subdir = self.subdir.replace('\\', '/')

    def __lt__(self, other: ProjectData) -> bool:
        return self.name < other.name


class SolutionFile:

    VCXPROJ_UUID = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"
    SUBDIR_UUID = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"

    def __init__(self, solution_path: Path):
        self.path = solution_path

        self._projects: dict[str, ProjectData] = {}
        self._subdirs: dict[str, str] = {}
        self.uuid = f"{{{str(uuid.uuid4())}}}".upper()

    def add_project(self, project: vcxproj.VcxProj, project_path: Path, subdir: T.Optional[str] = None,
                    build_solution_target: bool = False) -> None:
        subdir = '/'.join(s for s in (subdir, project.subdir) if s)

        project_data = ProjectData(
            project.uuid,
            project.name,
            project_path / project.subdir / project.filename,
            subdir=subdir,
            build_solution_target=build_solution_target,
        )

        if subdir:
            self.add_subdir(subdir)

        project_data.configurations.update(Configuration(d) for d in project.config_data)
        self._projects[project.uuid] = project_data

    def add_subdir(self, subdir: str) -> None:
        parts = subdir.replace('\\', '/').split('/')
        while parts:
            if (subpath := '/'.join(parts)) not in self._subdirs:
                self._subdirs[subpath] = f"{{{str(uuid.uuid5(uuid.NAMESPACE_URL, subpath))}}}".upper()
            parts.pop(-1)

    def remove_unknown_configurations(self, known_configurations: T.Collection[str]) -> None:
        for project_name in list(self._projects):
            project = self._projects[project_name]
            project.configurations = set(c for c in project.configurations if c.name in known_configurations)
            if not project.configurations:
                del self._projects[project_name]

    def remove_unknown_architectures(self, known_architectures: T.Collection[str]) -> None:
        for project_name in list(self._projects):
            project = self._projects[project_name]
            project.configurations = set(c for c in project.configurations if c.arch in known_architectures)
            if not project.configurations:
                del self._projects[project_name]

    def remove_current_configurations(self, configurations: T.Collection[vcxproj.Configuration]) -> None:
        for project_name in list(self._projects):
            project = self._projects[project_name]
            project.configurations = set(c for c in project.configurations if c in configurations)
            if not project.configurations:
                del self._projects[project_name]

    def load(self) -> None:
        contents = self.path.read_text(encoding='utf-8')
        m = re.search(r'SolutionGuid = (\{[0-9A-F-]+\})', contents)
        self.uuid = m[1]

        for m in re.finditer(rf'Project\("\{{{self.VCXPROJ_UUID}\}}"\) = "(.*)", "(.*)", "(.*)"', contents):
            project_data = ProjectData(m[3], m[2], Path(m[1]))
            self._projects[project_data.uuid] = project_data

        for m in re.finditer(rf'Project\("\{{{self.SUBDIR_UUID}\}}"\) = "(.*)", "(.*)", "(.*)"', contents):
            self._subdirs[m[2]] = m[3]

        for m in re.finditer(r'(\{[09A-F-]+\}).([\w-]+\|[\w+])\.Build\.0', contents):
            self._projects[m[1]].configurations.add(Configuration(m[2]))

    def write(self) -> None:
        # Reference: https://learn.microsoft.com/en-us/visualstudio/extensibility/internals/solution-dot-sln-file?view=vs-2022
        contents = [  # FIXME: versions here are totally arbitrary...
            'Microsoft Visual Studio Solution File, Format Version 12.00',
            '# Visual Studio Version 16',
            'VisualStudioVersion = 16.0.30204.135',
            'MinimumVisualStudioVersion = 10.0.40219.1',
        ]

        configurations = set()
        for project in sorted(self._projects.values()):
            contents.append(f'Project("{self.VCXPROJ_UUID}") = "{project.name}", "{project.path}", "{project.uuid}"')
            contents.append('EndProject')
            configurations.update(project.configurations)
        for subdir in sorted(self._subdirs):
            subdir_uuid = self._subdirs[subdir]
            parts = subdir.split('/')
            contents.append(f'Project("{self.SUBDIR_UUID}") = "{parts[-1]}", "{parts[-1]}", "{subdir_uuid}"')
            contents.append('EndProject')

        contents.append('Global')

        contents.append('	GlobalSection(SolutionConfigurationPlatforms) = preSolution')
        for config in sorted(configurations):
            contents.append(f'		{config} = {config}')
        contents.append('	EndGlobalSection')

        contents.append('	GlobalSection(ProjectConfigurationPlatforms) = postSolution')
        for project in sorted(self._projects.values()):
            for config in sorted(project.configurations):
                contents.append(f'		{project.uuid}.{config}.ActiveCfg = {config}')
                if project.build_solution_target:
                    contents.append(f'		{project.uuid}.{config}.Build.0 = {config}')
        contents.append('	EndGlobalSection')

        contents.append('	GlobalSection(SolutionProperties) = preSolution')
        contents.append('		HideSolutionNode = FALSE')
        contents.append('	EndGlobalSection')

        if self._subdirs:
            contents.append('	GlobalSection(NestedProjects) = preSolution')

            for subdir_name, subdir_uuid in self._subdirs.items():
                if '/' in subdir_name:
                    parent, _ = subdir_name.rsplit('/', maxsplit=1)
                    parent_uuid = self._subdirs[parent]
                    contents.append(f'		{subdir_uuid} = {parent_uuid}')

            for project in sorted(self._projects.values()):
                if project.subdir:
                    subdir_uuid = self._subdirs[project.subdir]
                    contents.append(f'		{project.uuid} = {subdir_uuid}')
            contents.append('	EndGlobalSection')

        contents.append('	GlobalSection(ExtensibilityGlobals) = postSolution')
        contents.append(f'		SolutionGuid = {self.uuid}')
        contents.append('	EndGlobalSection')

        contents.append('EndGlobal')

        self.path.write_text('\n'.join(contents), encoding='utf-8')
