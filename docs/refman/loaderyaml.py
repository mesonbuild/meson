# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

import typing as T
from pathlib import Path

from mesonbuild import mesonlib, mlog

from .loaderbase import LoaderBase
from .model import (
    Function,
    Kwarg,
    Method,
    Object,
    ObjectType,
    PosArg,
    ReferenceManual,
    Type,
    VarArgs,
)


class Template:
    d_feature_check: dict[str, T.Any] = {}
    s_posarg: dict[str, T.Any] = {}
    s_varargs: dict[str, T.Any] = {}
    s_kwarg: dict[str, T.Any] = {}
    s_function: dict[str, T.Any] = {}
    s_object: dict[str, T.Any] = {}

class StrictTemplate(Template):
    def __init__(self) -> None:
        from strictyaml import (  # type: ignore[import-untyped]
            Bool,
            EmptyList,
            Int,
            Map,
            MapPattern,
            Optional,
            OrValidator,
            Seq,
            Str,
        )

        d_named_object = {
            'name': Str(),
            'description': Str(),
        }

        d_feature_check = {
            Optional('since', default=''): Str(),
            Optional('deprecated', default=''): Str(),
        }

        self.s_posarg = Map({
            **d_feature_check,
            'description': Str(),
            'type': Str(),
            Optional('default', default=''): Str(),
        })

        self.s_varargs = Map({
            **d_named_object, **d_feature_check,
            'type': Str(),
            Optional('min_varargs', default=-1): Int(),
            Optional('max_varargs', default=-1): Int(),
        })

        self.s_kwarg = Map({
            **d_feature_check,
            'type': Str(),
            'description': Str(),
            Optional('required', default=False): Bool(),
            Optional('default', default=''): Str(),
        })

        self.s_function = Map({
            **d_named_object, **d_feature_check,
            'returns': Str(),
            Optional('notes', default=[]): OrValidator(Seq(Str()), EmptyList()),
            Optional('warnings', default=[]): OrValidator(Seq(Str()), EmptyList()),
            Optional('example', default=''): Str(),
            Optional('posargs'): MapPattern(Str(), self.s_posarg),
            Optional('optargs'): MapPattern(Str(), self.s_posarg),
            Optional('varargs'): self.s_varargs,
            Optional('posargs_inherit', default=''): Str(),
            Optional('optargs_inherit', default=''): Str(),
            Optional('varargs_inherit', default=''): Str(),
            Optional('kwargs'): MapPattern(Str(), self.s_kwarg),
            Optional('kwargs_inherit', default=[]): OrValidator(OrValidator(Seq(Str()), EmptyList()), Str()),
            Optional('arg_flattening', default=True): Bool(),
        })

        self.s_object = Map({
            **d_named_object, **d_feature_check,
            'long_name': Str(),
            Optional('extends', default=''): Str(),
            Optional('notes', default=[]): OrValidator(Seq(Str()), EmptyList()),
            Optional('warnings', default=[]): OrValidator(Seq(Str()), EmptyList()),
            Optional('example', default=''): Str(),
            Optional('methods'): Seq(self.s_function),
            Optional('is_container', default=False): Bool()
        })

class FastTemplate(Template):
    d_feature_check: dict[str, T.Any] = {
        'since': '',
        'deprecated': '',
    }

    s_posarg = {
        **d_feature_check,
        'default': '',
    }

    s_varargs: dict[str, T.Any] = {
        **d_feature_check,
        'min_varargs': -1,
        'max_varargs': -1,
    }

    s_kwarg = {
        **d_feature_check,
        'required': False,
        'default': '',
    }

    s_function = {
        **d_feature_check,
        'notes': [],
        'warnings': [],
        'example': '',
        'posargs': {},
        'optargs': {},
        'varargs': None,
        'posargs_inherit': '',
        'optargs_inherit': '',
        'varargs_inherit': '',
        'kwargs': {},
        'kwargs_inherit': [],
        'arg_flattening': True,
    }

    s_object = {
        **d_feature_check,
        'extends': '',
        'notes': [],
        'warnings': [],
        'example': '',
        'methods': [],
        'is_container': False,
    }

class LoaderYAML(LoaderBase):
    def __init__(self, yaml_dir: Path, strict: bool=True) -> None:
        super().__init__()
        self.yaml_dir = yaml_dir
        self.func_dir = self.yaml_dir / 'functions'
        self.elem_dir = self.yaml_dir / 'elementary'
        self.objs_dir = self.yaml_dir / 'objects'
        self.builtin_dir = self.yaml_dir / 'builtins'
        self.modules_dir = self.yaml_dir / 'modules'
        self.strict = strict

        template: Template
        if self.strict:
            import strictyaml
            def loader(file: str, template: T.Any, label: str) -> dict:
                r: dict = strictyaml.load(file, template, label=label).data
                return r

            self._load = loader
            template = StrictTemplate()
        else:
            import yaml
            from yaml import CLoader
            def loader(file: str, template: T.Any, label: str) -> dict:
                return {**template, **yaml.load(file, Loader=CLoader)}

            self._load = loader
            template = FastTemplate()

        self.template = template

    def _fix_default(self, v: dict) -> None:
        if v["default"] is False:
            v["default"] = "false"
        elif v["default"] is True:
            v["default"] = "true"
        else:
            v["default"] = str(v["default"])

    def _process_function_base(self, raw: dict, obj: Object | None = None) -> Function:
        # Handle arguments
        posargs = raw.pop('posargs', {})
        optargs = raw.pop('optargs', {})
        varargs = raw.pop('varargs', None)
        kwargs = raw.pop('kwargs', {})

        # Fix kwargs_inherit
        if isinstance(raw['kwargs_inherit'], str):
            raw['kwargs_inherit'] = [raw['kwargs_inherit']]

        # Parse args
        posargs_mapped: list[PosArg] = []
        optargs_mapped: list[PosArg] = []
        varargs_mapped: VarArgs | None = None
        kwargs_mapped: dict[str, Kwarg] = {}

        for k, v in posargs.items():
            if not self.strict:
                v = {**self.template.s_posarg, **v}
                self._fix_default(v)
            v['type'] = Type(v['type'])
            posargs_mapped += [PosArg(name=k, **v)]

        for k, v in optargs.items():
            if not self.strict:
                v = {**self.template.s_posarg, **v}
                self._fix_default(v)
            v['type'] = Type(v['type'])
            optargs_mapped += [PosArg(name=k, **v)]

        for k, v in kwargs.items():
            if not self.strict:
                v = {**self.template.s_kwarg, **v}
                self._fix_default(v)
            v['type'] = Type(v['type'])
            kwargs_mapped[k] = Kwarg(name=k, **v)

        if varargs is not None:
            if not self.strict:
                varargs = {**self.template.s_varargs, **varargs}
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

    def _load_function(self, path: Path, obj: Object | None = None) -> Function:
        path_label = path.relative_to(self.yaml_dir).as_posix()
        mlog.log('Loading', mlog.bold(path_label))
        raw = self._load(self.read_file(path), self.template.s_function, label=path_label)
        return self._process_function_base(raw)

    def _load_object(self, obj_type: ObjectType, path: Path) -> Object:
        path_label = path.relative_to(self.yaml_dir).as_posix()
        mlog.log('Loading', mlog.bold(path_label))
        raw = self._load(self.read_file(path), self.template.s_object, label=path_label)

        def as_methods(mlist: list[Function]) -> list[Method]:
            res: list[Method] = []
            for i in mlist:
                assert isinstance(i, Method)
                res += [i]
            return res

        methods = raw.pop('methods', [])
        obj = Object(methods=[], obj_type=obj_type, **raw)

        newmethods = []
        for x in methods:
            if not self.strict:
                x = {**self.template.s_function, **x}
            newmethods += [self._process_function_base(x, obj)]
        obj.methods = as_methods(newmethods)
        return obj

    def _load_module(self, path: Path) -> list[Object]:
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
        mlog.log('Loading YAML reference manual')
        with mlog.nested():
            manual = ReferenceManual(
                functions=[self._load_function(x) for x in self.func_dir.iterdir()],
                objects=mesonlib.listify([
                    [self._load_object(ObjectType.ELEMENTARY, x) for x in self.elem_dir.iterdir()],
                    [self._load_object(ObjectType.RETURNED, x) for x in self.objs_dir.iterdir()],
                    [self._load_object(ObjectType.BUILTIN, x) for x in self.builtin_dir.iterdir()],
                    [self._load_module(x) for x in self.modules_dir.iterdir()]
                ], flatten=True)
            )

            if not self.strict:
                mlog.warning('YAML reference manual loaded using the best-effort fastyaml loader.  Results are not guaranteed to be stable or correct.')

            return manual
