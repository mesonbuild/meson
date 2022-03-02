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

import os
import pathlib
import typing as T
from mesonbuild import mesonlib
from mesonbuild.build import CustomTarget, CustomTargetIndex, GeneratedList, Target
from mesonbuild.compilers import detect_compiler_for, Compiler
from mesonbuild.interpreter import Interpreter
from mesonbuild.interpreterbase.decorators import ContainerTypeInfo, FeatureDeprecated, FeatureNew, KwargInfo, typed_pos_args, typed_kwargs
from mesonbuild.mesonlib import version_compare, MachineChoice
from . import NewExtensionModule, ModuleReturnValue, ModuleState

class JavaModule(NewExtensionModule):
    @FeatureNew('Java Module', '0.60.0')
    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
            'generate_native_header': self.generate_native_header,
            'generate_native_headers': self.generate_native_headers,
        })

    def __get_java_compiler(self, state: ModuleState) -> Compiler:
        if 'java' not in state.environment.coredata.compilers[MachineChoice.BUILD]:
            detect_compiler_for(state.environment, 'java', MachineChoice.BUILD)
        return state.environment.coredata.compilers[MachineChoice.BUILD]['java']

    @FeatureDeprecated('java.generate_native_header', '0.62.0', 'Use java.generate_native_headers instead')
    @typed_pos_args('java.generate_native_header', (str, mesonlib.File))
    @typed_kwargs('java.generate_native_header', KwargInfo('package', str, default=None))
    def generate_native_header(self, state: ModuleState, args: T.Tuple[T.Union[str, mesonlib.File]],
                               kwargs: T.Dict[str, T.Optional[str]]) -> ModuleReturnValue:
        package = kwargs.get('package')

        if isinstance(args[0], mesonlib.File):
            file = args[0]
        else:
            file = mesonlib.File.from_source_file(state.source_root, state.subdir, args[0])

        if package:
            header = f'{package.replace(".", "_")}_{pathlib.Path(file.fname).stem}.h'
        else:
            header = f'{pathlib.Path(file.fname).stem}.h'

        javac = self.__get_java_compiler(state)

        target = CustomTarget(
            os.path.basename(header),
            state.subdir,
            state.subproject,
            mesonlib.listify([
                javac.exelist,
                '-d',
                '@PRIVATE_DIR@',
                '-h',
                state.subdir,
                '@INPUT@',
            ]),
            [file],
            [header],
            backend=state.backend,
        )
        # It is only known that 1.8.0 won't pre-create the directory. 11 and 16
        # do not exhibit this behavior.
        if version_compare(javac.version, '1.8.0'):
            pathlib.Path(state.backend.get_target_private_dir_abs(target)).mkdir(parents=True, exist_ok=True)

        return ModuleReturnValue(target, [target])

    @FeatureNew('java.generate_native_headers', '0.62.0')
    @typed_pos_args('java.generate_native_headers',
        varargs=(str, mesonlib.File, Target, CustomTargetIndex, GeneratedList))
    @typed_kwargs('java.generate_native_headers',
        KwargInfo('classes', ContainerTypeInfo(list, str), default=[], listify=True,
            required=True),
        KwargInfo('package', str, default=None))
    def generate_native_headers(self, state: ModuleState, args: T.Tuple[T.List[mesonlib.FileOrString]],
                               kwargs: T.Dict[str, T.Optional[str]]) -> ModuleReturnValue:
        classes = T.cast('T.List[str]', kwargs.get('classes'))
        package = kwargs.get('package')

        headers: T.List[str] = []
        for clazz in classes:
            underscore_clazz = clazz.replace(".", "_")
            if package:
                headers.append(f'{package.replace(".", "_")}_{underscore_clazz}.h')
            else:
                headers.append(f'{underscore_clazz}.h')

        javac = self.__get_java_compiler(state)

        command = mesonlib.listify([
            javac.exelist,
            '-d',
            '@PRIVATE_DIR@',
            '-h',
            state.subdir,
            '@INPUT@',
        ])

        prefix = classes[0] if not package else package

        target = CustomTarget(f'{prefix}-native-headers', state.subdir, state.subproject, command,
                              sources=args[0], outputs=headers, backend=state.backend)

        # It is only known that 1.8.0 won't pre-create the directory. 11 and 16
        # do not exhibit this behavior.
        if version_compare(javac.version, '1.8.0'):
            pathlib.Path(state.backend.get_target_private_dir_abs(target)).mkdir(parents=True, exist_ok=True)

        return ModuleReturnValue(target, [target])

def initialize(*args: T.Any, **kwargs: T.Any) -> JavaModule:
    return JavaModule(*args, **kwargs)
