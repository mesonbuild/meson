from pathlib import Path
import re
import sys
import typing as T


STRUCTURE = {
    'vs': {
        'projects': {
            'myprog': {
                'myprog.vcxproj': None,
                'myprog.vcxproj.filters': None,
                'myprog.vcxproj.user': None,
            },
            '_ALL.vcxproj': None,
            '_ALL.vcxproj.filters': None,
            '_ALL.vcxproj.user': None,
        },
        'VsSolution.sln': None,
    }
}


def test_generated_structure(base: Path, structure: T.Dict[str, T.Optional[dict]]) -> T.Union[str, int]:
    for filename, contents in structure.items():
        if contents is None:
            if not (base / filename).is_file():
                return f'{base / filename} not found'
        else:
            if not (base / filename).is_dir():
                return f'{base / filename} not found'
            result = test_generated_structure(base / filename, structure[filename])
            if result:
                return result
    return 0


def test_has_include_dir(vcxproj: Path, include_dir: Path):
    contents = vcxproj.read_text(encoding='utf-8')
    includes = re.search(r'<NMakeIncludeSearchPath>(.*)</NMakeIncludeSearchPath>', contents)
    if not includes:
        return f'Include paths not found in {vcxproj}'
    if include_dir in map(Path, includes[1].split(';')):
        return 0
    return f'{include_dir} not found in {includes[1]}'


def test_has_macros(vcxproj: Path, macros: T.List[str]):
    contents = vcxproj.read_text(encoding='utf-8')
    defines = re.search(r'<NMakePreprocessorDefinitions>(.*)</NMakePreprocessorDefinitions>', contents)
    if not defines:
        return f'Preprocessor definitions not found in {vcxproj}'
    macro_list = defines[1].split(';')
    for macro in macros:
        if macro not in macro_list:
            return f'Macro {macro} not in {defines[1]}'
    return 0


def main():
    base = Path(__file__).parent
    myprog_vcxproj = base / 'vs' / 'projects' / 'myprog' / 'myprog.vcxproj'
    return (test_generated_structure(base, STRUCTURE)
            or test_has_include_dir(myprog_vcxproj, base / 'include')
            or test_has_macros(myprog_vcxproj, ('GLOBAL', 'PROJECT', 'LOCAL')))


if __name__ == '__main__':
    sys.exit(main())
