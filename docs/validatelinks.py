#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

import sys
import re
import aiohttp
import asyncio

LINK = re.compile(r'\[(?P<name>[^\]]+)\]\((?P<url>.*?)\)')


async def fetch(session, name, url, timeout):
    try:
        async with session.get(url, timeout=timeout) as r:
            if not r.ok:
                return (name, url, r.status)
    except Exception as e:
        return (name, url, str(e))


async def main(filename):
    with open(filename) as f:
        text = f.read()
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession() as session:
            tasks = []
            for link in LINK.finditer(text):
                name, url = link.groups()
                name = name.replace('\n', ' ')
                task = asyncio.ensure_future(fetch(session, name, url, timeout))
                tasks.append(task)
            responses = asyncio.gather(*tasks)
            errors = [r for r in await responses if r is not None]
        bad = False
        for name, url, result in errors:
            if re.match(r'https://github.com/(search|topics/)', url) and result == 429:
                print(f'"{name}" {url} {result} (ignored)')
            else:
                print(f'"{name}" {url} {result}')
                bad = True
        if errors:
            sys.exit(int(bad))


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
