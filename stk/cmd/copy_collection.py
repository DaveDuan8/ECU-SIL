r"""
stk/cmd/copy_collection
-----------------------

*copy collection* copies a collection from Oracle DB (val_global_admin) per default or an sqlite into an sqlite.
  - The collection to be copied will be placed at root at destination sqlite db.
  - All shared (sub-)collections are changed to be `normal` collections at destination.
  - In case your collection already exists, collection will be update by new values,
    older entries such as subcollections and recordings will no be deleted, but rather updated and extended.


*call syntax example*
C:\\> python copy_collection.py -n "MFC123_validation" -d d:\\data\\MFC123.sqlite

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.8 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/07/13 13:21:42CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath
from os.path import dirname, abspath, join
from argparse import ArgumentParser, FileType, RawDescriptionHelpFormatter

# - import STK modules ------------------------------------------------------------------------------------------------
STKBASE = abspath(join(dirname(__file__), "..\\.."))
if STKBASE not in spath:
    spath.append(STKBASE)

from stk.db.cat.collection import copy_collection_data
from stk.util.helper import DefSpace


# - functions ---------------------------------------------------------------------------------------------------------
def parse_args():
    """
    just calling the operation and saving the result
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-n", "--name", required=True, type=str, help="name of catalog to copy")
    opts.add_argument("-s", "--source", default="VGA", type=str, help="source database to copy catalog from, "
                                                                      "other options: 'MFC4XX', 'ARS4XX'")
    opts.add_argument("-d", "--destination", required=True, type=FileType("r"),
                      help="destination database to copy catalog to")
    opts.add_argument("-p", "--purge", default=False, action="store_true", help="purge / cleanup collections b4 copy")
    opts.add_argument("-R", "--rectobj", default=False, action="store_true", help="include rect objects to be copied")
    opts.add_argument("-S", "--scenarios", default=False, action="store_true", help="include scenarios to be copied")
    opts.add_argument("-G", "--genlabels", default=False, action="store_true", help="include gen-labels to be copied")
    opts.add_argument("-C", "--camlabels", nargs=2, default=None, help="include cam-labels to be copied, "
                                                                       "arguments: <tablebase> <component>")

    args = opts.parse_args(namespace=DefSpace())
    args.destination.close()
    args.destination = args.destination.name
    args.use_print = True
    return args


# - main --------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    """main main"""
    sexit(copy_collection_data(**parse_args()))


"""
CHANGE LOG:
-----------
$Log: copy_collection.py  $
Revision 1.8 2016/07/13 13:21:42CEST Mertens, Sven (uidv7805) 
more options...
Revision 1.7 2016/07/13 13:01:27CEST Mertens, Sven (uidv7805)
change namings: gen-labels, cam-labels
Revision 1.6 2016/07/08 10:15:36CEST Mertens, Sven (uidv7805)
use namespace to get kwargs
Revision 1.5 2016/06/17 12:21:08CEST Mertens, Sven (uidv7805)
import fix
Revision 1.4 2016/06/17 12:04:34CEST Mertens, Sven (uidv7805)
commands usually just are parsing
Revision 1.3 2016/04/05 17:40:24CEST Mertens, Sven (uidv7805)
adding cleanup flag
Revision 1.2 2016/04/05 15:50:39CEST Mertens, Sven (uidv7805)
no pylints...
Revision 1.1 2016/04/05 15:47:44CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.2 2016/03/31 16:31:34CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.1 2016/03/29 17:38:06CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
"""
