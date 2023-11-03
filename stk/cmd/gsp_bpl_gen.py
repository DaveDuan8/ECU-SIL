r"""
gsp_bpl_gen.py
--------------

This script scans through folder \\lifs010\data\ARS4T0\FOT\_Import with given subfolder
for ARS4T0_transfer.json and transfer.json files and generates an output file with recordings from destination path.
Supported output formats are bpl, csv and txt.

options:
  # root (base) folder to start search from
  -b <base folder>
    default: \\lifs010\data\ARS4T0\FOT\_Import

  # subfolders to restrict search to
  -d <subfolder 0>[ <subfolder 1>[ ...]]
    default: user input
    specials:
        -d today
        -d *
        -d <subfolder 0>-<subfolder n>

  # file containing names for subsubfolders to restrict search even more
  -l <label file>
    default: None

  # output file for recordings found (and existing)
  -o <output.file>
    default: <.\recordings.bpl>

  # output file for recordings not found (or not existing)
  -i <inverse.file>
    default: None

  # recording file extentions to take care of
  -e <ext0>[ <ext1>[ ...]]
    default: rec rrec


:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.4 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/03/30 16:44:08CEST $
"""

__author__ = 'uidv7805'
__version__ = ": 0.0 $".partition(':')[2].strip('$ ')

# - Python imports ----------------------------------------------------------------------------------------------------
from os import listdir, walk
from os.path import exists, join, abspath, splitext
from sys import exit as sexit
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from simplejson import load
from datetime import datetime
from re import search
from itertools import chain


# - classes / functions ------------------------------------------------------------------------------------------------
class RecordingWriter(object):
    """todo:"""
    def __init__(self, outfile):
        """init output file"""
        self._file = outfile
        self._eo = True
        self._ext = None

        if self._file:
            if not hasattr(self._file, "write"):
                self._file = open(outfile, 'wb')
                self._eo = False

            self._ext = splitext(self._file.name)[1]

        self._recs = []

    def append(self, rec):
        """append a recording"""
        self._recs.append(rec)

    def __enter__(self):
        """being able to use with statement
        """
        return self

    def __exit__(self, *_):
        """close file"""
        self.close()

    def close(self):
        """close file"""
        if self._ext == ".csv":
            self._file.write("recfilepath\r\n")

        recs = set(self._recs)  # uniquify

        if self._ext in (".csv", ".txt"):
            for i in recs:
                self._file.write("%s\r\n" % i)

        elif self._ext == ".bpl":
            top = Element('BatchList')
            for i in recs:
                sub = SubElement(top, "BatchEntry", {'fileName': i})
                SubElement(sub, "SectionList")
            self._file.write(parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8'))

        if not self._eo:
            self._file.close()


def parse_args():
    """parse command line arguments and returns parsed arguments
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-b", "--base", default=r"\\lifs010\data\ARS4T0\FOT\_Import", type=str,
                      help="date to create bpl from (subfolder)")
    opts.add_argument("-d", "--date", nargs='*', default=['*'], type=str,
                      help="date to create bpl from (subfolder)")
    opts.add_argument("-e", "--extentions", nargs='+', default=["rec", "rrec"], type=str,
                      help="specify recoding file name extentions to take care of")
    opts.add_argument("-l", "--hdlabels", default=None, type=FileType('r'),
                      help="line by line file with HDD labels to limit search")
    opts.add_argument("-i", "--inverse", default=None, type=FileType('wb'),
                      help="output file, supports bpl, csv, txt")
    opts.add_argument("-o", "--out", default="recordings.bpl", type=FileType('wb'),
                      help="output file, supports bpl, csv, txt")
    args = opts.parse_args()

    # argument decryption
    if args.date == ["today"]:
        args.date = [datetime.now().strftime("%Y%m%d")]
    elif args.date == ['*']:
        args.date = listdir(args.base)
    elif len(args.date) == 1 and search(r"^\d{8}-\d{8}", args.date[0]):
        beg, end = args.date[0].split('-')
        args.date = [d for d in listdir(args.base) if beg <= d <= end]
    args.date = [join(args.base, d) for d in args.date]

    if args.hdlabels is None:
        args.hdlabels = ".*"
    else:
        args.hdlabels = "^(" + "|".join([l.strip() for l in args.hdlabels.readlines() if len(l) > 2]) + ")$"

    return args


# - main ---------------------------------------------------------------------------------------------------------------
def scanner(args):
    """folder / file scanning

    :param args: parsed arguments
    """
    cnt = 0
    with RecordingWriter(args.out) as recw, RecordingWriter(args.inverse) as invw:
        for date in args.date:
            for dirname, subnames, filenames in walk(date):
                subnames[:] = [d for d in subnames if search(args.hdlabels, d)]
                filenames[:] = [f for f in filenames if f in ("transfer.json", "ARS4T0_transfer.json")]

                for fname in filenames:
                    with open(abspath(join(dirname, fname))) as fpt:
                        objs = load(fpt)['objects']
                        if type(objs) == dict:
                            objs = list(chain(*objs.values()))
                        for obj in objs:
                            dfn = obj['destination filepath']
                            if splitext(dfn)[1][1:] in args.extentions:
                                try:
                                    if exists(dfn):
                                        recw.append(dfn)
                                    else:
                                        invw.append(dfn)
                                except:
                                    pass
                                cnt += 1

    return cnt


# - main main ---------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(scanner(parse_args()))


"""
CHANGE LOG:
-----------
$Log: gsp_bpl_gen.py  $
Revision 1.4 2016/03/30 16:44:08CEST Mertens, Sven (uidv7805) 
reducing some pylints
Revision 1.3 2015/09/22 11:42:24CEST Mertens, Sven (uidv7805)
even more docu
--- Added comments ---  uidv7805 [Sep 22, 2015 11:42:24 AM CEST]
Change Package : 363145:1 http://mks-psad:7002/im/viewissue?selection=363145
Revision 1.2 2015/09/22 11:09:30CEST Mertens, Sven (uidv7805)
change to write test as we want to write, not read
--- Added comments ---  uidv7805 [Sep 22, 2015 11:09:31 AM CEST]
Change Package : 363145:1 http://mks-psad:7002/im/viewissue?selection=363145
Revision 1.1 2015/09/17 11:52:16CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
