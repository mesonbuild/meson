// SPDX-License-Identifier: Apache-2.0
// Copyright The Meson development team

// Tiny helper used by Meson on Windows to set environment variables before
// executing a command, equivalent to `env(1)` on POSIX systems.
//
// Usage: meson_env KEY1=VAL1 [KEY2=VAL2 ...] COMMAND [ARG ...]
//
// All leading arguments that look like `K=V` (and where K is a valid env-var
// name) are consumed as assignments; the first non-assignment argument and
// everything after it becomes the command to execute. The child process'
// exit code is propagated.

use std::env;
use std::process::{exit, Command};

fn is_assignment(arg: &str) -> Option<(&str, &str)> {
    let (k, v) = arg.split_once('=')?;
    if k.is_empty() {
        return None;
    }
    let first = k.as_bytes()[0];
    if !(first.is_ascii_alphabetic() || first == b'_') {
        return None;
    }
    if !k.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_') {
        return None;
    }
    Some((k, v))
}

fn main() {
    let mut args = env::args().skip(1);
    let mut cmd: Option<String> = None;
    while let Some(arg) = args.next() {
        match is_assignment(&arg) {
            Some((k, v)) => env::set_var(k, v),
            None => {
                cmd = Some(arg);
                break;
            }
        }
    }
    let cmd = match cmd {
        Some(c) => c,
        None => {
            eprintln!("meson_env: no command given");
            exit(2);
        }
    };
    let rest: Vec<String> = args.collect();
    let status = match Command::new(&cmd).args(&rest).status() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("meson_env: failed to execute {cmd}: {e}");
            exit(127);
        }
    };
    exit(status.code().unwrap_or(1));
}
