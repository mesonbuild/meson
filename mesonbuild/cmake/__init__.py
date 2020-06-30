# Copyright 2019 The Meson development team

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

__all__ = [
    'CMakeClient',
    'CMakeExecutor',
    'CMakeException',
    'CMakeFileAPI',
    'CMakeInterpreter',
    'CMakeTarget',
    'CMakeTraceLine',
    'CMakeTraceParser',
    'SingleTargetOptions',
    'TargetOptions',
    'parse_generator_expressions',
    'language_map',
    'cmake_defines_to_args',
]

from .common import CMakeException, SingleTargetOptions, TargetOptions, cmake_defines_to_args
from .client import CMakeClient
from .executor import CMakeExecutor
from .fileapi import CMakeFileAPI
from .generator import parse_generator_expressions
from .interpreter import CMakeInterpreter, language_map
from .traceparser import CMakeTarget, CMakeTraceLine, CMakeTraceParser
