# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

"""Minimal protobom SBOM writer.

Emits a protobom Document as protobuf binary. Only varint and
length-delimited wire types are needed, so the encoder is hand-rolled and
Meson gains no protobuf runtime dependency.
"""

from __future__ import annotations

import os
import time
import typing as T

from . import build, coredata
from .mesonlib import MesonException

# protobom field numbers, from protobom/api/sbom.proto.
_DOC_METADATA = 1
_DOC_NODE_LIST = 2
_META_NAME = 3
_META_DATE = 4
_META_TOOLS = 5
_TOOL_NAME = 1
_TOOL_VERSION = 2
_TS_SECONDS = 1
_NODELIST_NODES = 1
_NODELIST_EDGES = 2
_NODE_ID = 1
_NODE_NAME = 3
_NODE_VERSION = 4
_NODE_IDENTIFIERS = 28
_EDGE_TYPE = 1
_EDGE_FROM = 2
_EDGE_TO = 3
_EDGE_DEPENDS_ON = 10
_ID_PURL = 1


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _int(field: int, n: int) -> bytes:
    return _tag(field, 0) + _varint(n)


def _bytes(field: int, data: bytes) -> bytes:
    return _tag(field, 2) + _varint(len(data)) + data


def _str(field: int, s: str) -> bytes:
    return _bytes(field, s.encode())


def _msg(field: int, parts: T.Iterable[bytes]) -> bytes:
    return _bytes(field, b''.join(parts))


def _map_int_str(field: int, items: T.Mapping[int, str]) -> bytes:
    return b''.join(_msg(field, [_int(1, k), _str(2, items[k])])
                    for k in sorted(items))


def _purl(name: str, version: T.Optional[str]) -> T.Optional[str]:
    if not version or version == 'unknown':
        return None
    # ponytail: no percent-encoding; Meson target names are path-safe.
    return f'pkg:generic/{name}@{version}'


def _dependency_id(name: str, version: T.Optional[str]) -> str:
    purl = _purl(name, version)
    if purl:
        return purl
    if version and version != 'unknown':
        return f'{name}@{version}'
    return name


def _node(nid: str, name: str, version: T.Optional[str], purl: T.Optional[str]) -> bytes:
    parts = [_str(_NODE_ID, nid), _str(_NODE_NAME, name)]
    if version and version != 'unknown':
        parts.append(_str(_NODE_VERSION, version))
    if purl:
        parts.append(_map_int_str(_NODE_IDENTIFIERS, {_ID_PURL: purl}))
    return _msg(_NODELIST_NODES, parts)


def _timestamp() -> int:
    sde = os.environ.get('SOURCE_DATE_EPOCH')
    if sde:
        try:
            return int(sde)
        except ValueError:
            pass
    return int(time.time())


def build_document(b: build.Build, timestamp: int) -> bytes:
    version = b.project_version or ''
    nodes: T.Dict[str, bytes] = {}
    edges: T.Set[T.Tuple[str, str]] = set()

    for target in b.get_targets().values():
        nid = target.get_id()
        nodes[nid] = _node(nid, target.name, version, _purl(target.name, version))
        if not isinstance(target, build.BuildTarget):
            continue
        for dep in target.get_all_link_deps():
            edges.add((nid, dep.get_id()))
        for dep in target.get_external_deps():
            dname = dep.get_name()
            dver = dep.get_version()
            dpurl = _purl(dname, dver)
            did = _dependency_id(dname, dver)
            if did not in nodes:
                nodes[did] = _node(did, dname, dver, dpurl)
            edges.add((nid, did))

    meta = [
        _str(_META_NAME, b.project_name),
        _msg(_META_DATE, [_int(_TS_SECONDS, timestamp)]),
        _msg(_META_TOOLS, [_str(_TOOL_NAME, 'meson'),
                           _str(_TOOL_VERSION, coredata.version)]),
    ]
    node_list = [nodes[k] for k in sorted(nodes)]
    node_list += [_msg(_NODELIST_EDGES, [_int(_EDGE_TYPE, _EDGE_DEPENDS_ON),
                                         _str(_EDGE_FROM, f), _str(_EDGE_TO, t)])
                  for f, t in sorted(edges)]
    return _msg(_DOC_METADATA, meta) + _msg(_DOC_NODE_LIST, node_list)


def emit(b: build.Build, path: str) -> None:
    data = build_document(b, _timestamp())
    try:
        with open(path, 'wb') as f:
            f.write(data)
    except OSError as e:
        raise MesonException(f'Could not write SBOM to {path}: {e}')
