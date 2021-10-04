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

from .loaderbase import LoaderBase
from .model import (
    Type,
    PosArg,
    VarArgs,
    Kwarg,
    Function,
    Method,
    ObjectType,
    Object,
    ReferenceManual,
)

from mesonbuild import mlog
from mesonbuild import mesonlib

from strictyaml import Map, MapPattern, Optional, Str, Seq, Int, Bool, load, EmptyList, OrValidator
from pathlib import Path
import typing as T

d_named_object = {
    'name': Str(),
    'description': Str(),
}

d_feture_check = {
    Optional('since', default=''): Str(),
    Optional('deprecated', default=''): Str(),
}

s_posarg = Map({
    **d_feture_check,
    'description': Str(),
    'type': Str(),
    Optional('default', default=''): Str(),
})

s_varargs = Map({
    **d_named_object, **d_feture_check,
    'type': Str(),
    Optional('min_varargs', default=-1): Int(),
    Optional('max_varargs', default=-1): Int(),
})

s_kwarg = Map({
    **d_feture_check,
    'type': Str(),
    'description': Str(),
    Optional('required', default=False): Bool(),
    Optional('default', default=''): Str(),
})

s_function = Map({
    **d_named_object, **d_feture_check,
    'returns': Str(),
    Optional('notes', default=[]): OrValidator(Seq(Str()), EmptyList()),
    Optional('warnings', default=[]): OrValidator(Seq(Str()), EmptyList()),
    Optional('example', default=''): Str(),
    Optional('posargs'): MapPattern(Str(), s_posarg),
    Optional('optargs'): MapPattern(Str(), s_posarg),
    Optional('varargs'): s_varargs,
    Optional('posargs_inherit', default=''): Str(),
    Optional('optargs_inherit', default=''): Str(),
    Optional('varargs_inherit', default=''): Str(),
    Optional('kwargs'): MapPattern(Str(), s_kwarg),
    Optional('kwargs_inherit', default=[]): OrValidator(OrValidator(Seq(Str()), EmptyList()), Str()),
})

s_object = Map({
    **d_named_object, **d_feture_check,
    'long_name': Str(),
    Optional('extends', default=''): Str(),
    Optional('notes', default=[]): OrValidator(Seq(Str()), EmptyList()),
    Optional('warnings', default=[]): OrValidator(Seq(Str()), EmptyList()),
    Optional('example', default=''): Str(),
    Optional('methods'): Seq(s_function),
    Optional('is_container', default=False): Bool()
})

class LoaderYAML(LoaderBase):
    def __init__(self, yaml_dir: Path) -> None:
        super().__init__()
        self.yaml_dir = yaml_dir
        self.func_dir = self.yaml_dir / 'functions'
        self.elem_dir = self.yaml_dir / 'elementary'
        self.objs_dir = self.yaml_dir / 'objects'
        self.builtin_dir = self.yaml_dir / 'builtins'
        self.modules_dir = self.yaml_dir / 'modules'

    def _process_function_base(self, raw: T.OrderedDict, obj: T.Optional[Object] = None) -> Function:
        # Handle arguments
        posargs = raw.pop('posargs', {})
        optargs = raw.pop('optargs', {})
        varargs = raw.pop('varargs', None)
        kwargs = raw.pop('kwargs', {})

        # Fix kwargs_inherit
        if isinstance(raw['kwargs_inherit'], str):
            raw['kwargs_inherit'] = [raw['kwargs_inherit']]

        # Parse args
        posargs_mapped: T.List[PosArg] = []
        optargs_mapped: T.List[PosArg] = []
        varargs_mapped: T.Optional[VarArgs] = None
        kwargs_mapped: T.Dict[str, Kwarg] = {}

        for k, v in posargs.items():
            v['type'] = Type(v['type'])
            posargs_mapped += [PosArg(name=k, **v)]

        for k, v in optargs.items():
            v['type'] = Type(v['type'])
            optargs_mapped += [PosArg(name=k, **v)]

        for k, v in kwargs.items():
            v['type'] = Type(v['type'])
            kwargs_mapped[k] = Kwarg(name=k, **v)

        if varargs is not None:
            varargs['type'] = Type(varargs['type'])
            varargs_mapped = VarArgs(**varargs)

        raw['returns'] = Type(raw['returns'])

        # Build function object
        if obj is not None:
            return Method(
                posargs=posargs_mapped,
                optargs=optargs_mapped,
                varargs=varargs_mapped,
                kwargs=kwargs_mapped,
                obj=obj,
                **raw,
            )
        return Function(
            posargs=posargs_mapped,
            optargs=optargs_mapped,
            varargs=varargs_mapped,
            kwargs=kwargs_mapped,
            **raw,
        )

    def _load_function(self, path: Path, obj: T.Optional[Object] = None) -> Function:
        path_label = path.relative_to(self.yaml_dir).as_posix()
        mlog.log('Loading', mlog.bold(path_label))
        raw = load(self.read_file(path), s_function, label=path_label).data
        return self._process_function_base(raw)

    def _load_object(self, obj_type: ObjectType, path: Path) -> Object:
        path_label = path.relative_to(self.yaml_dir).as_posix()
        mlog.log(f'Loading', mlog.bold(path_label))
        raw = load(self.read_file(path), s_object, label=path_label).data

        def as_methods(mlist: T.List[Function]) -> T.List[Method]:
            res: T.List[Method] = []
            for i in mlist:
                assert isinstance(i, Method)
                res += [i]
            return res

        methods = raw.pop('methods', [])
        obj = Object(methods=[], obj_type=obj_type, **raw)
        obj.methods = as_methods([self._process_function_base(x, obj) for x in methods])
        return obj

    def _load_module(self, path: Path) -> T.List[Object]:
        assert path.is_dir()
        module = self._load_object(ObjectType.MODULE, path / 'module.yaml')
        objs = []
        for p in path.iterdir():
            if p.name == 'module.yaml':
                continue
            obj = self._load_object(ObjectType.RETURNED, p)
            obj.defined_by_module = module
            objs += [obj]
        return [module, *objs]

    def load_impl(self) -> ReferenceManual:
        mlog.log('Loading YAML refererence manual')
        with mlog.nested():
            return ReferenceManual(
                functions=[self._load_function(x) for x in self.func_dir.iterdir()],
                objects=mesonlib.listify([
                    [self._load_object(ObjectType.ELEMENTARY, x) for x in self.elem_dir.iterdir()],
                    [self._load_object(ObjectType.RETURNED, x) for x in self.objs_dir.iterdir()],
                    [self._load_object(ObjectType.BUILTIN, x) for x in self.builtin_dir.iterdir()],
                    [self._load_module(x) for x in self.modules_dir.iterdir()]
                ], flatten=True)
            )
