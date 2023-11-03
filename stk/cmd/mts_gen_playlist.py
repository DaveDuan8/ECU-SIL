"""
mts_gen_playlist
----------------

**Create a mts batch playlist from given input files**

**Features:**
    - Creates a mts playlist out of given rec file paths.

**UseCase:**
 Typically used for a Simulation Job which has a StatisticCollector inside.
 Used to create a *.bpl for a StatisticCollector Task. Just in case
 if it is needed for debugging.

**Usage:**

mts_gen_playlist.py -o my_playlist.bpl hugo.rec berta.rec anna.rec

Parameters:
 -o OutFile
    Name of the Batchplaylist output file. if no name is specified, a
    default one is used. (e.g. mts_playlist.bpl)
 RecFileUrl(s)
    Space separated urls from *.rec files which should be inside the target
    *.bpl.

:org:           Continental AG
:author:        Robert Hecker
                Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:03:49CEST $
"""
# Import Python Modules --------------------------------------------------------
import os
import sys
from optparse import OptionParser

# Add PyLib Folder to System Paths ---------------------------------------------
STK_FOLDER = os.path.abspath(os.path.join(os.path.split(__file__)[0], r"..\.."))
if STK_FOLDER not in sys.path:
    sys.path.append(STK_FOLDER)

# Import STK Modules -----------------------------------------------------------
from stk.mts.bpl import Bpl, BplListEntry


# Main function ----------------------------------------------------------------
def main():
    """main function"""
    error = 0

    parser = OptionParser(usage="%prog [Options] RecFileUrl(s)")

    parser.add_option("-o",
                      dest="OutFile",
                      default='mts_playlist.bpl',
                      help="Filename of the mts batch playlist")

    opt = parser.parse_args()

    files = opt[1]
    bpl_writer = Bpl(str(opt[0].OutFile))
    for file_ in files:
        bpl_writer.append(BplListEntry(str(file_)))
    bpl_writer.write()

    return error


# Main Entry Point -------------------------------------------------------------
if __name__ == "__main__":

    sys.exit(main())

"""
CHANGE LOG:
-----------
$Log: mts_gen_playlist.py  $
Revision 1.1 2015/04/23 19:03:49CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.9 2014/06/13 09:22:21CEST Hecker, Robert (heckerr) 
Some more updates in epydoc.
--- Added comments ---  heckerr [Jun 13, 2014 9:22:22 AM CEST]
Change Package : 238264:1 http://mks-psad:7002/im/viewissue?selection=238264
Revision 1.8 2014/06/12 16:56:09CEST Hecker, Robert (heckerr)
Updated epydoc documentation.
--- Added comments ---  heckerr [Jun 12, 2014 4:56:10 PM CEST]
Change Package : 238265:1 http://mks-psad:7002/im/viewissue?selection=238265
Revision 1.7 2014/04/15 14:02:33CEST Hecker, Robert (heckerr)
some adaptions to pylint.
--- Added comments ---  heckerr [Apr 15, 2014 2:02:33 PM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.6 2013/09/26 19:13:28CEST Hecker, Robert (heckerr)
Removed some pep8 Errors.
--- Added comments ---  heckerr [Sep 26, 2013 7:13:29 PM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
Revision 1.5 2013/09/25 09:20:19CEST Hecker, Robert (heckerr)
Removed some Errors and corrected stk import.
--- Added comments ---  heckerr [Sep 25, 2013 9:20:20 AM CEST]
Change Package : 197303:1 http://mks-psad:7002/im/viewissue?selection=197303
"""
