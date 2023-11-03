"""
folder2bpl.py
-------------

Script to generate a bpl out of a base folder full of any file existing in there.

options available:

-r
  # recursive search
-f <path/to/folder>
  # root folder to search in
-b <path/to/file.bpl>
  # bpl file to create
-p <pattern>
  # file pattern to limit search to


:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.7 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/03/30 13:24:00CEST $
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from os import listdir, walk
from os.path import exists, isfile, join
from sys import exit as sexit
from fnmatch import fnmatch
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


# - classes / functions -----------------------------------------------------------------------------------------------
def write_bpl(recs, bpl):
    """writes one bpl

    :param recs: list of recordings
    :param bpl: file name to write bpl to
    """
    top = Element('BatchList')
    cnt = 0
    for rec in recs:
        sub = SubElement(top, "BatchEntry", {'fileName': rec})
        SubElement(sub, "SectionList")
        cnt += 1

    if cnt:
        bpl.write(parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8'))

    return cnt


# - main --------------------------------------------------------------------------------------------------------------
def main():
    """main"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-f", "--folder", required=True, type=str, help="input folder to scan")
    opts.add_argument("-p", "--pattern", default="*.*", type=str, help="file pattern to use")
    opts.add_argument("-r", "--recursive", default=False, action="store_true", help="go through recursively")
    opts.add_argument("-b", "--bpl", required=True, type=FileType('wb'), help="bpl file to write to")
    args = opts.parse_args()

    if not exists(args.folder):
        print("input folder '%s' doesn't exist!" % args.folder)
        return -1

    recs = []
    if args.recursive:
        for root, _, files in walk(args.folder):
            files = [join(root, f) for f in files
                     if any([fnmatch(f, p) for p in args.pattern.split(';')]) and isfile(join(root, f))]

            recs.extend(files)
    else:
        recs = [join(args.folder, f) for f in listdir(args.folder)
                if any([fnmatch(f, p) for p in args.pattern.split(';')]) and isfile(join(args.folder, f))]

    cnt = write_bpl(recs, args.bpl)
    print("%d files written to '%s'" % (cnt, args.bpl.name))

    return cnt


# - main main ---------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(main())


"""
CHANGE LOG:
-----------
$Log: bpl_from_folder.py  $
Revision 1.7 2016/03/30 13:24:00CEST Mertens, Sven (uidv7805) 
pylint fix
Revision 1.6 2015/09/25 15:41:26CEST Hospes, Gerd-Joachim (uidv8815)
fix module docu: option list
--- Added comments ---  uidv8815 [Sep 25, 2015 3:41:26 PM CEST]
Change Package : 376211:1 http://mks-psad:7002/im/viewissue?selection=376211
Revision 1.5 2015/09/22 11:46:17CEST Mertens, Sven (uidv7805)
even more docu
--- Added comments ---  uidv7805 [Sep 22, 2015 11:46:17 AM CEST]
Change Package : 363145:1 http://mks-psad:7002/im/viewissue?selection=363145
Revision 1.4 2015/09/17 17:46:00CEST Hospes, Gerd-Joachim (uidv8815)
add recursive search for files
--- Added comments ---  uidv8815 [Sep 17, 2015 5:46:01 PM CEST]
Change Package : 377210:1 http://mks-psad:7002/im/viewissue?selection=377210
Revision 1.3 2015/09/08 08:36:34CEST Mertens, Sven (uidv7805)
remove try / except as covered by argparser's option
--- Added comments ---  uidv7805 [Sep 8, 2015 8:36:34 AM CEST]
Change Package : 371672:3 http://mks-psad:7002/im/viewissue?selection=371672
Revision 1.2 2015/09/07 16:29:24CEST Mertens, Sven (uidv7805)
fix the n
--- Added comments ---  uidv7805 [Sep 7, 2015 4:29:25 PM CEST]
Change Package : 371672:2 http://mks-psad:7002/im/viewissue?selection=371672
Revision 1.1 2015/09/07 16:22:12CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
