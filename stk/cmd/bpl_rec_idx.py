"""
bpl_rec_idx.py
--------------

bpl_rec_idx will find all indices of a file or part of path or file from given bpl.

:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 15:39:13CET $
"""

__author__ = 'uidv7805'
__version__ = "$Revision: 1.2 $".partition(':')[2].strip('$ ')

# - Python imports ----------------------------------------------------------------------------------------------------
from sys import exit as sexit
from xml.etree.ElementTree import parse
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter


# - function ---------------------------------------------------------------------------------------------------------
def get_bpl_rec_idx(bpl_file_path, search_str):
    """ search bpl file (xml format) for a string in the file name

    :param bpl_file_path: path and file name of bpl file (xml format)
    :type  bpl_file_path: str
    :param search_str:    text to search for in rec file names of bpl
    :type  search_str:    str
    :return: list of indices containing search str
    """
    return [i for i, r in enumerate(parse(bpl_file_path).getroot()) if search_str in r.get("fileName")]


# - main --------------------------------------------------------------------------------------------------------------
def main():
    """main"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-b", "--bpl", required=True, type=FileType('r'), help="input bpl to scan through")
    opts.add_argument("-r", "--rec", required=True, type=str, help="recording to search for")
    args = opts.parse_args()

    idxs = get_bpl_rec_idx(args.bpl, args.rec)
    print("recording '%s' could match at indices %s" % (args.rec, ", ".join(str(i) for i in idxs)))

    return 0


# - main main ---------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(main())


"""
CHANGE LOG:
-----------
$Log: bpl_rec_idx.py  $
Revision 1.2 2015/12/07 15:39:13CET Mertens, Sven (uidv7805) 
removing pep8 errors
Revision 1.1 2015/07/28 17:38:02CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
