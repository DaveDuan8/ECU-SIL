r"""
cat_files_adaptation
--------------------

adapt your sqlite database to update CAT_FILES' FILEPATH from Oracle changed recordings' filenames

*call syntax example*
C:\> python cat_files_adaptation.py <sqlite db file>

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/11/17 16:03:19CET $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os.path import abspath
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import defaultdict


# - import STK modules -------------------------------------------------------------------------------------------------
STKDIR = abspath(r"..\..")
if STKDIR not in sys.path:
    sys.path.append(STKDIR)

from stk.db.db_common import BaseDB


# - main ---------------------------------------------------------------------------------------------------------------
def main():
    """entry point of application:
        opens VGA and your sqlite, compares oldnames of Oracle and tries to update your sqlite paths accordingly
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("sqlite", type=str, help="sqlite file name")
    args = opts.parse_args()

    with BaseDB(args.sqlite) as sqdb, BaseDB("VGA") as vga:
        meas = defaultdict(list)
        # read updates from Oracle
        for rec in vga.executex("SELECT MEASID, OLDNAME, NEWNAME FROM CAT_DMT_FILES_MOVES ORDER BY MEASID, MOVEID"):
            meas[rec[0]].append(rec[1:])

        # reorganize renamings to latest one
        renames = {}
        for rec, names in meas.iteritems():
            renames[names[0][0]] = names[-1][1]

        # update users sqlite DB
        cnt = 0
        for rec in sqdb.executex("SELECT MEASID, FILEPATH FROM CAT_FILES"):
            if rec[1] in renames:
                if sqdb.execute("UPDATE CAT_FILES SET FILEPATH = :newpath WHERE MEASID = :meas",
                                newpath=renames[rec[1]], meas=rec[0]) > 0:
                    print("updated measid %d: %s" % (rec[0], renames[rec[1]]))
                else:
                    print("ERROR: failed to update measid %d with %s" % (rec[0], renames[rec[1]]))

    print("done, updated %d recording(s)" % cnt)


# - main --------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()


"""
CHANGE LOG:
-----------
$Log: cat_files_adaptation.py  $
Revision 1.2 2017/11/17 16:03:19CET Mertens, Sven (uidv7805) 
long line fix
Revision 1.1 2017/11/17 16:02:26CET Mertens, Sven (uidv7805) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
