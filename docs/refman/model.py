# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

import typing as T
from dataclasses import dataclass, field
from enum import Enum


# Utils
@dataclass
class NamedObject:
    name: str
    description: str

    @property
    def hidden(self) -> bool:
        return self.name.startswith('_')

@dataclass
class FeatureCheck:
    since: str
    deprecated: str

@dataclass
class DataTypeInfo:
    data_type: 'Object'
    holds: T.Optional['Type']

@dataclass
class Type:
    raw: str
    resolved: list[DataTypeInfo] = field(init=False, default_factory=list)


# Arguments
@dataclass
class ArgBase(NamedObject, FeatureCheck):
    type: Type

@dataclass
class PosArg(ArgBase):
    default: str

@dataclass
class VarArgs(ArgBase):
    min_varargs: int
    max_varargs: int

@dataclass
class Kwarg(ArgBase):
    required: bool
    default: str


# Function
@dataclass
class Function(NamedObject, FeatureCheck):
    notes: list[str]
    warnings: list[str]
    returns: Type
    example: str
    posargs: list[PosArg]
    optargs: list[PosArg]
    varargs: VarArgs | None
    kwargs: dict[str, Kwarg]
    posargs_inherit: str
    optargs_inherit: str
    varargs_inherit: str
    kwargs_inherit: list[str]
    arg_flattening: bool

@dataclass
class Method(Function):
    obj: 'Object'


# Types and objects
class ObjectType(Enum):
    ELEMENTARY = 0
    BUILTIN = 1
    MODULE = 2
    FUNCTIONS = 3
    RETURNED = 4

@dataclass
class Object(NamedObject, FeatureCheck):
    notes: list[str]
    warnings: list[str]
    long_name: str
    example: str
    obj_type: ObjectType
    methods: list[Method]
    is_container: bool
    extends: str
    extends_obj: T.Optional['Object'] = None
    defined_by_module: T.Optional['Object'] = None
    returned_by: list[Function | Method] = field(default_factory=list)
    extended_by: list['Object'] = field(default_factory=list)
    inherited_methods: list[Method] = field(default_factory=list)

# ROOT
@dataclass
class ReferenceManual:
    functions: list[Function]
    objects: list[Object]
