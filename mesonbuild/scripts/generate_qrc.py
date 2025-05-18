import os
import argparse
import typing as T
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('--output')
parser.add_argument("--prefix")
parser.add_argument('sources', default=[], nargs='*')

def run(argv: T.List[str]) -> int:
    options, args = parser.parse_known_args(argv)

    rcc = ET.Element('RCC')
    qresource = ET.SubElement(rcc, 'qresource')

    if options.prefix:
        qresource.set("prefix", options.prefix)

    for source in options.sources:
        ET.SubElement(qresource, 'file').text = source

    tree = ET.ElementTree(rcc)
    ET.indent(tree, space='  ', level=0)
    tree.write(os.path.join(options.output))

    return 0
