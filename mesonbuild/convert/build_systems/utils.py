#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import re


def substitute_inputs_into_string(cmd: str, inputs: T.List[str]) -> str:
    return cmd.replace('@INPUT@', ' '.join(inputs))


def substitute_indexed_inputs_into_string(cmd: str, inputs: T.List[str]) -> str:
    def _get_input_by_index(match: re.Match) -> str:
        index_str = match.group(1)
        return inputs[int(index_str)]

    return re.sub(r'@INPUT(\d+)@', _get_input_by_index, cmd)


def substitute_outputs_into_string(cmd: str, outputs: T.List[str]) -> str:
    return cmd.replace('@OUTPUT@', ' '.join(outputs))


def substitute_indexed_outputs_into_string(cmd: str, outputs: T.List[str]) -> str:
    def _get_output_by_index(match: re.Match) -> str:
        index = int(match.group(1))
        return outputs[index]

    return re.sub(r'@OUTPUT(\d+)@', _get_output_by_index, cmd)
