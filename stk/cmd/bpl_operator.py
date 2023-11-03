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

.. python::

    bpl_operator.py or -i main.bpl empty.bpl -o singles.bpl

Use for the empty.bpl::

  <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <BatchList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="batchlist.xsd">
  </BatchList>

This script does not use any other STK imports and just needs a Python 2.7 installation.

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/09/18 16:16:16CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from sys import exit as sexit, stderr
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from re import match
from StringIO import StringIO


# - classes -----------------------------------------------------------------------------------------------------------
class PlayList(list):
    """
    class to provide list of bpl files and operator methods
    """
    def __init__(self, path, sensitive=False, mode='r'):
        """
        :param path: path to file
        :param sensitive: when comparing to another PlayList, do it sensitive
        :param mode: read=r, write=w
        """
        list.__init__(self)

        self._path = open(path, mode=mode) if not hasattr(path, "read") else path

        if mode == 'r':
            try:
                self.extend([node.get("fileName") for node in parse(self._path).getroot()])
            except:
                stderr.write("error reading %s, assuming it's an empty one!" % self._path.name)

        self._sensitive = sensitive

    def __enter__(self):
        """with..."""
        return self

    def __exit__(self, *_):
        """...with"""
        self.close()

    def __or__(self, other):
        """let's do | (or) operator
        """
        return list(set(self.files()).union(set(other.files())))

    def __xor__(self, other):
        """let's do ^ (xor) operator
        """
        return list(set(self.files()).symmetric_difference(set(other.files())))

    def __and__(self, other):
        """let's do & (and) operator
        """
        return list(set(self.files()).intersection(set(other.files())))

    def __sub__(self, other):
        """let's do - (sub) operator
        """
        return list(set(self.files()).difference(set(other.files())))

    def files(self):
        """remove additional dotted unc parts
        """
        if self._sensitive:
            return self

        paths = []
        for file_ in self:
            mtc = match(r"(?i)(\\\\\w*)(\.[\w.]*)?(\\.*)", file_)
            paths.append((mtc.group(1) + mtc.group(3)).lower() if mtc else file_)

        return paths

    def close(self):
        """close file"""
        if hasattr(self._path, "read"):
            self._path.close()
            self._path = None

    def write(self):
        """writes file out"""
        top = Element('BatchList')
        for file_ in self:
            sub = SubElement(top, "BatchEntry", {'fileName': file_})
            SubElement(sub, "SectionList")

        self._path.seek(0)
        self._path.write(parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8'))


# - main --------------------------------------------------------------------------------------------------------------
def main():
    """
    just calling the operation and saving the result
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument(dest="task", choices=['xor', 'or', 'and', 'sub'], type=str,
                      help="what to do (diff,merge,common,only in 1st)?")
    opts.add_argument("-i", dest="infiles", nargs='+', type=FileType('rb'), help="input files to process")
    opts.add_argument("-o", dest="outfile", required=True, type=FileType('wb'), help="output file")
    opts.add_argument("-s", dest="sensitive", default=False, action="store_true",
                      help="compare files with case-sensitivity")
    # opts.add_argument("-")
    args = opts.parse_args()
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
        trgt.extend(arith[args.task](src1, src2))
        trgt.write()

    return 0

# - main --------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(main())


"""
CHANGE LOG:
-----------
$Log: bpl_operator.py  $
Revision 1.5 2015/09/18 16:16:16CEST Hospes, Gerd-Joachim (uidv8815) 
handle every file with wrong xml structure as empty file
- Added comments -  uidv8815 [Sep 18, 2015 4:16:17 PM CEST]
Change Package : 378411:1 http://mks-psad:7002/im/viewissue?selection=378411
Revision 1.4 2015/06/30 11:09:44CEST Mertens, Sven (uidv7805)
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:09:45 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.3 2015/05/18 13:22:59CEST Mertens, Sven (uidv7805)
fix for empty file
--- Added comments ---  uidv7805 [May 18, 2015 1:23:00 PM CEST]
Change Package : 338373:1 http://mks-psad:7002/im/viewissue?selection=338373
Revision 1.2 2015/05/18 11:45:10CEST Mertens, Sven (uidv7805)
support for one file only, the other one is assumed to be empty
--- Added comments ---  uidv7805 [May 18, 2015 11:45:11 AM CEST]
Change Package : 338373:1 http://mks-psad:7002/im/viewissue?selection=338373
Revision 1.1 2015/04/23 19:03:43CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.4 2015/04/23 15:19:59CEST Hospes, Gerd-Joachim (uidv8815)
enhance docu
--- Added comments ---  uidv8815 [Apr 23, 2015 3:20:00 PM CEST]
Change Package : 328888:1 http://mks-psad:7002/im/viewissue?selection=328888
Revision 1.3 2015/04/01 13:48:24CEST Hospes, Gerd-Joachim (uidv8815)
docu update
--- Added comments ---  uidv8815 [Apr 1, 2015 1:48:25 PM CEST]
Change Package : 324228:1 http://mks-psad:7002/im/viewissue?selection=324228
Revision 1.2 2015/01/19 13:28:12CET Mertens, Sven (uidv7805)
variable name fix
--- Added comments ---  uidv7805 [Jan 19, 2015 1:28:12 PM CET]
Change Package : 296850:1 http://mks-psad:7002/im/viewissue?selection=296850
Revision 1.1 2015/01/15 16:51:55CET Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/cmd/project.pj
Revision 1.2 2014/10/09 14:37:18CEST Mertens, Sven (uidv7805)
adding docu
--- Added comments ---  uidv7805 [Oct 9, 2014 2:37:19 PM CEST]
Change Package : 270435:1 http://mks-psad:7002/im/viewissue?selection=270435
Revision 1.1 2014/10/09 14:01:08CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/cmd/project.pj
"""
