from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import re
import sys
import typing as T
import uuid
import xml.etree.ElementTree as ET


def xml_indent(tree: ET.Element, space: str = '  ', level: int = 0) -> None:
    """Backported from a more recent Python"""
    if isinstance(tree, ET.ElementTree):
        tree = tree.getroot()
    if level < 0:
        raise ValueError(f'Initial indentation level must be >= 0, got {level}')
    if not (tree and len(tree)):
        return

    # Reduce the memory consumption by reusing indentation strings.
    indentations = ['\n' + level * space]

    def _indent_children(elem: ET.Element, level: int) -> None:
        # Start a new indentation level for the first child.
        child_level = level + 1
        try:
            child_indentation = indentations[child_level]
        except IndexError:
            child_indentation = indentations[level] + space
            indentations.append(child_indentation)

        if not elem.text or not elem.text.strip():
            elem.text = child_indentation

        for child in elem:
            if len(child):
                _indent_children(child, child_level)
            if not child.tail or not child.tail.strip():
                child.tail = child_indentation

        # Dedent after the last child by overwriting the previous indentation.
        if not child.tail.strip():
            child.tail = indentations[level]

    _indent_children(tree, 0)


@dataclass(eq=True, frozen=True)
class Configuration:

    name: str
    arch: str
    is_debug: bool

    def __str__(self) -> str:
        return f'{self.name}|{self.arch}'

    @property
    def condition(self) -> str:
        return f"'$(Configuration)|$(Platform)'=='{self!s}'"

    def evolve(self, **kwargs: T.Union[str, bool]) -> Configuration:
        d = asdict(self)
        d.update(kwargs)
        return Configuration(**d)

    def __lt__(self, other: Configuration) -> bool:
        return (self.name, self.arch) < (other.name, other.arch)


@dataclass
class ConfigurationData:

    config: Configuration
    output: T.Optional[str]
    build_dir: Path
    toolset: T.Optional[str] = None

    macros: T.List[str] = field(default_factory=list)
    include_directories: T.List[str] = field(default_factory=list)
    additional_options: T.List[str] = field(default_factory=list)
    search_paths: T.List[str] = field(default_factory=list)
    has_output: bool = True

    def __lt__(self, other: ConfigurationData) -> bool:
        return str(self.config) < str(other.config)


class VcxProj:

    NS: str = 'http://schemas.microsoft.com/developer/msbuild/2003'

    def __init__(self, name: str, source_dir: Path, subdir: T.Optional[str]):
        self.name: str = name
        self.uuid = f'{{{str(uuid.uuid4())}}}'.upper()
        self.source_dir: Path = source_dir
        self.subdir = subdir or ''
        self.config_data: T.Dict[str, ConfigurationData] = {}

        self._files: T.Dict[Path, str] = {}

        self.filename: str = f'{self.name}.vcxproj'
        self.filterfile: str = f'{self.filename}.filters'
        self.userfile: str = f'{self.filename}.user'

        self.generated = False

    def add_config(self, config: ConfigurationData) -> None:
        self.config_data[str(config.config)] = config

    def _add_file(self, file: str, category: str) -> None:
        p = Path(file)
        if not p.is_absolute():
            p = self.source_dir / p
        self._files[p] = category

    def add_sources(self, sources: T.Iterable[str]) -> None:
        for f in sources:
            self._add_file(f, 'ClCompile')

    def add_headers(self, headers: T.Iterable[str]) -> None:
        for f in headers:
            self._add_file(f, 'ClInclude')

    def add_extra_files(self, extras: T.Iterable[str]) -> None:
        for f in extras:
            self._add_file(f, 'None')

    def iter_files(self) -> T.Generator[T.Tuple[str, str], None, None]:
        for f in sorted(self._files):
            yield str(f), self._files[f]

    def generate(self, output_path: Path, config: ConfigurationData, known_configurations: T.List[str], known_architectures: T.List[str]) -> None:
        project_dir = output_path / self.subdir

        self.read(project_dir, known_configurations, known_architectures)
        self.add_config(config)
        self.write(project_dir)
        self.generated = True

    def _read_opt_node(self, parent: ET.Element, name: str, default: T.Optional[str] = None) -> T.Optional[str]:
        node = parent.find(f'{{{self.NS}}}{name}')
        if node is None:
            return default
        return node.text or default

    def read(self, project_dir: Path,
             known_configurations: T.Optional[T.List[str]] = None,
             known_architectures: T.Optional[T.List[str]] = None) -> None:
        filepath = project_dir / self.filename
        if not filepath.exists():
            return

        try:
            root = ET.parse(project_dir / self.filename).getroot()
        except ET.ParseError as e:
            print(f"Unable to parse {project_dir / self.filename}: {e}", file=sys.stderr)
            return

        self.uuid = root.find(f'.//{{{self.NS}}}ProjectGuid').text

        for config_node in root.iterfind(f'.//{{{self.NS}}}ProjectConfiguration'):
            config = config_node.findtext(f"{{{self.NS}}}Configuration")
            arch = config_node.findtext(f"{{{self.NS}}}Platform")

            if known_configurations is not None and config not in known_configurations:
                continue
            if known_architectures is not None and config not in known_architectures:
                continue

            configuration = Configuration(config, arch, False)

            for config_node in root.iterfind(f'.//{{{self.NS}}}PropertyGroup'):
                condition = config_node.attrib.get("Condition")
                if condition != configuration.condition:
                    continue

                label = config_node.attrib.get('Label')

                if label == 'UserMacros':
                    build_dir = config_node.find(f'{{{self.NS}}}BuildDir').text
                    search_paths = self._read_opt_node(config_node, 'DllPaths', '').split(';')

                elif label == "Configuration":
                    toolset = self._read_opt_node(config_node, 'PlatformToolset')
                    is_debug = config_node.find(f'{{{self.NS}}}UseDebugLibraries').text
                    if is_debug == 'true':
                        configuration = configuration.evolve(is_debug=True)

                elif label is None:
                    include_directories = self._read_opt_node(config_node, 'NMakeIncludeSearchPath', '').split(';')
                    macros = self._read_opt_node(config_node, 'NMakePreprocessorDefinitions', '').split(' ')
                    additional_options = self._read_opt_node(config_node, 'AdditionalOptions', '').split(';')
                    build_cmd = self._read_opt_node(config_node, 'NMakeBuildCommandLine', '')
                    m = re.fullmatch(r'ninja -C (\S+) (\S+)', build_cmd)
                    output = m[2] if m else None

            config_data = ConfigurationData(configuration, output, Path(build_dir), toolset,
                                            macros, include_directories, additional_options, search_paths)
            self.add_config(config_data)

        self.add_sources(n.attrib.get("Include") for n in root.iterfind(f'.//{{{self.NS}}}ClCompile'))
        self.add_headers(n.attrib.get("Include") for n in root.iterfind(f'.//{{{self.NS}}}ClInclude'))
        self.add_extra_files(n.attrib.get("Include") for n in root.iterfind(f'.//{{{self.NS}}}None'))

    def write(self, project_dir: Path) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        self._write_project_file(project_dir)
        self._write_filters_file(project_dir)
        self._write_user_file(project_dir)

    def _xml_project(self, **kwargs: str) -> ET.Element:
        kwargs.setdefault('xmlns', self.NS)
        root = ET.Element('Project', attrib=kwargs)
        return root

    @staticmethod
    def _write_xml(path: Path, xml_root: ET.Element) -> None:
        xml_indent(xml_root)  # with Python 3.9:  ET.indent(xml_root)
        xml = ET.tostring(xml_root, encoding='UTF-8', xml_declaration=True)
        path.write_bytes(xml)

    def _write_project_file(self, project_dir: Path) -> None:
        root = self._xml_project(DefaultTargets='Build')

        project_configurations = ET.SubElement(root, 'ItemGroup', attrib={'Label': 'ProjectConfigurations'})
        for config, data in sorted(self.config_data.items()):
            pc = ET.SubElement(project_configurations, 'ProjectConfiguration', attrib={'Include': config})
            ET.SubElement(pc, 'Configuration').text = data.config.name
            ET.SubElement(pc, 'Platform').text = data.config.arch

        globals_group = ET.SubElement(root, 'PropertyGroup', attrib={'Label': 'Globals'})
        # FIXME: what is minimum version? Should it be a param?
        ET.SubElement(globals_group, 'VCProjectVersion').text = '15.0'
        ET.SubElement(globals_group, 'ProjectGuid').text = self.uuid
        ET.SubElement(globals_group, 'Keyword').text = 'MakeFileProj'

        ET.SubElement(root, 'Import', attrib={'Project': '$(VCTargetsPath)\\Microsoft.Cpp.Default.props'})

        for data in sorted(self.config_data.values()):
            conf = ET.SubElement(root, 'PropertyGroup', attrib={
                                 'Label': 'Configuration', 'Condition': data.config.condition})
            ET.SubElement(conf, 'ConfigurationType').text = 'Makefile'
            ET.SubElement(conf, 'UseDebugLibraries').text = str(data.config.is_debug).lower()

            if data.toolset:
                ET.SubElement(conf, 'PlatformToolset').text = data.toolset

        ET.SubElement(root, 'Import', attrib={'Project': '$(VCTargetsPath)\\Microsoft.Cpp.props'})
        ET.SubElement(root, 'ImportGroup', attrib={'Label': 'ExtensionSettings'})
        ET.SubElement(root, 'ImportGroup', attrib={'Label': 'Shared'})

        for data in sorted(self.config_data.values()):
            prop_sheets = ET.SubElement(root, 'ImportGroup', attrib={
                                        'Label': 'PropertySheets', 'Condition': data.config.condition})
            ET.SubElement(prop_sheets, 'Import', attrib={
                          'Label': 'LocalAppDataPlatform', 'Project': '$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props', 'Condition': "exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')"})

        for data in sorted(self.config_data.values()):
            user_macros = ET.SubElement(root, 'PropertyGroup', attrib={
                                        'Label': 'UserMacros', 'Condition': data.config.condition})
            ET.SubElement(user_macros, 'BuildDir').text = str(data.build_dir)
            ET.SubElement(user_macros, 'DllPaths').text = ';'.join(data.search_paths)

        for data in sorted(self.config_data.values()):
            compile_cmd = ET.SubElement(root, 'PropertyGroup', attrib={'Condition': data.config.condition})
            if data.output:
                ET.SubElement(compile_cmd, 'NMakeBuildCommandLine').text = f'ninja -C "$(BuildDir)" {data.output}'
                if data.has_output:
                    ET.SubElement(compile_cmd, 'NMakeOutput').text = str(data.build_dir / data.output)
                ET.SubElement(
                    compile_cmd, 'NMakeReBuildCommandLine').text = 'ninja -C "$(BuildDir)" clean && ninja -C "$(BuildDir)" {data.output}'
            ET.SubElement(compile_cmd, 'NMakeCleanCommandLine').text = 'ninja -C "$(BuildDir)" clean'
            if data.macros:
                ET.SubElement(compile_cmd, 'NMakePreprocessorDefinitions').text = ';'.join(data.macros)
            if data.include_directories:
                ET.SubElement(compile_cmd, 'NMakeIncludeSearchPath').text = ';'.join(str(d) for d in data.include_directories)
            if data.additional_options:
                ET.SubElement(compile_cmd, 'AdditionalOptions').text = ' '.join(data.additional_options)
            ET.SubElement(compile_cmd, 'LocalDebuggerWorkingDirectory').text = '$(BuildDir)'
            ET.SubElement(compile_cmd, 'LocalDebuggerEnvironment').text = 'PATH=$(DllPaths)'

        cat_nodes: T.Dict[str, ET.Element] = {}
        for filename, category in self.iter_files():
            node = cat_nodes.get(category)
            if not node:
                node = ET.SubElement(root, 'ItemGroup')
                cat_nodes[category] = node
            ET.SubElement(node, category, attrib={'Include': filename})

        ET.SubElement(root, 'Import', attrib={'Project': '$(VCTargetsPath)\\Microsoft.Cpp.targets'})
        ET.SubElement(root, 'ImportGroup', attrib={'Label': 'ExtensionTargets'})

        self._write_xml(project_dir / self.filename, root)

    def _write_filters_file(self, project_dir: Path) -> None:

        def _dirname(file: T.Union[Path, str]) -> str:
            return str(Path(file).relative_to(self.source_dir).parent)

        subdirs = set()
        for file in sorted(self._files):
            dirname = _dirname(file)
            if dirname != '.':
                subdirs.add(dirname)
                for p in Path(dirname).parents:
                    if str(p) != '.' and str(p) not in subdirs:
                        subdirs.add(str(p))
                        continue
                    break

        root = self._xml_project(ToolsVersion='4.0')  # FIXME...
        filter_list = ET.SubElement(root, "ItemGroup")
        for dirname in sorted(subdirs):
            ET.SubElement(filter_list, "Filter", attrib={"Include": dirname})

        file_list = ET.SubElement(root, "ItemGroup")
        for filename, category in self.iter_files():
            file_node = ET.SubElement(file_list, category, attrib={"Include": filename})
            dirname = _dirname(filename)
            if dirname != '.':
                ET.SubElement(file_node, "Filter").text = dirname

        self._write_xml(project_dir / self.filterfile, root)

    def _write_user_file(self, project_dir: Path) -> None:
        filepath = project_dir / self.userfile
        if filepath.exists():
            return  # do not override user file

        root = self._xml_project(ToolsVersion='Current')
        ET.SubElement(root, 'PropertyGroup')
        self._write_xml(filepath, root)
