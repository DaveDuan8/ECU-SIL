r"""
bpl_operator
------------

**Bpl Operator** supports easy command line calls to diff, merge etc. bpl files with bpl syntax (xml style).
(\*.ini files are not supported)

**call syntax example**

C:\> python bpl_operator <op> -i <first.bpl> <second.bpl> -o <result.bpl> [-s]

This program does an operation on 2 BPL based files.
Result of operation is saved into an output BPL based file.

Attention: it does not handle sections! The output will not contain any sections.

The result will not contain duplicates of a recordings.

Option -s is intended to strictly use fileNames inside BPL's as they are,
otherwise, unc paths will be aligned and case insensitive comparison will take place.

<op> := and | or | xor | sub

  - *xor*: will contain files from either input (diff),
  - *or*:  will contain files from both inputs (merge),
  - *and*: will contain files common to both inputs,
  - *sub*: will contain files from first input which are not inside second input

As the result does not contain duplicated recordings this can also be used to clean up
all duplicate recordings in a bpl file by running

.. code::

    bpl_operator.py or -i main.bpl empty.bpl -o singles.bpl

Use for the empty.bpl::

  <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <BatchList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="batchlist.xsd">
  </BatchList>

This script does not use any other HPC imports and just needs a Python installation.
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from __future__ import print_function
from sys import exit as sexit, stderr, argv
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from re import match
from six import PY3
if PY3:
    from io import StringIO
else:
    from StringIO import StringIO  # pylint: disable=E0401


# - classes -----------------------------------------------------------------------------------------------------------
class PlayList(list):
    """class to provide list of bpl files and operator methods"""

    def __init__(self, path, sensitive=False, mode='r'):
        """
        :param str path: path to file
        :param bool sensitive: when comparing to another PlayList, do it sensitive
        :param str mode: read=r, write=w
        """
        list.__init__(self)

        self._path = open(path, mode=mode) if not hasattr(path, "read") else path

        if mode == 'r':
            try:
                self.extend([node.get("fileName") for node in parse(self._path).getroot()])
            except Exception:
                stderr.write("error reading {}, assuming it's an empty one!".format(self._path.name))

        self._sensitive = sensitive

    def __enter__(self):
        """with..."""
        return self

    def __exit__(self, *_):
        """...with"""
        self.close()

    def __or__(self, other):
        """let's do | (or) operator"""
        return list(set(self.files()).union(set(other.files())))

    def __xor__(self, other):
        """let's do ^ (xor) operator"""
        return list(set(self.files()).symmetric_difference(set(other.files())))

    def __and__(self, other):
        """let's do & (and) operator"""
        return list(set(self.files()).intersection(set(other.files())))

    def __sub__(self, other):
        """let's do - (sub) operator"""
        return list(set(self.files()).difference(set(other.files())))

    def files(self):
        """remove additional dotted unc parts"""
        if self._sensitive:
            return self

        paths = []
        for file_ in self:
            mtc = match(r"(?i)(\\\\\w*)(\.[\w.]*)?(\\.*)", file_)
            paths.append((mtc.group(1) + mtc.group(3)).lower() if mtc else file_.lower())

        return paths

    def close(self):
        """close file"""
        if hasattr(self._path, "read"):
            self._path.close()
            self._path = None

    def write(self):
        """write file"""
        top = Element('BatchList')
        for file_ in self:
            sub = SubElement(top, "BatchEntry", {'fileName': file_})
            SubElement(sub, "SectionList")

        self._path.seek(0)
        self._path.write(parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8'))


# - main --------------------------------------------------------------------------------------------------------------
def main():  # pragma: nocover
    """just calling the operation and saving the result"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument(dest="arith", choices=['xor', 'or', 'and', 'sub'], type=str,
                      help="what to do (diff,merge,common,only in 1st)?")
    opts.add_argument("-i", dest="infiles", nargs='+', type=FileType('rb'), help="input files to process")
    opts.add_argument("-o", dest="outfile", required=True, type=FileType('wb'), help="output file")
    opts.add_argument("-s", dest="sensitive", default=False, action="store_true",
                      help="compare files with case-sensitivity")
    # opts.add_argument("-")
    args = opts.parse_args(None if argv[1:] else ['-h'])
    arith = {"xor": lambda x, y: x ^ y, "or": lambda x, y: x | y, "and": lambda x, y: x & y, "sub": lambda x, y: x - y}

    infiles = args.infiles
    if len(infiles) == 1:
        infiles.append(StringIO('<?xml version="1.0" encoding="UTF-8"?><BatchList/>'))
    elif len(infiles) > 2:
        print("sorry, only 2 files at max are supported by now.")
        return 1

    with PlayList(infiles[0], args.sensitive) as src1, PlayList(infiles[1], args.sensitive) as src2, \
            PlayList(args.outfile, mode='w') as trgt:
        src1.close()
        src2.close()
        trgt.extend(arith[args.arith](src1, src2))
        trgt.write()

    return 0


# - main --------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(main())
