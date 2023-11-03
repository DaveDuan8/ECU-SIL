"""
stk/db/db_connect.py
--------------------

Old database interface for the requested package object,

use BaseDB derived classes as listed in `db_common` module instead,
it is much easier to configure and use.

For DB connections in Valf suites use observer `DbLinker`.


:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:22CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from inspect import currentframe, getmembers, isclass
from os.path import abspath, join, dirname, isfile

DB_SUPPORT_IMAGE = True

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import ERROR_TOLERANCE_NONE, PluginBaseDB, GetFullTablePrefix
from stk.util.helper import list_folders
from stk.util.logger import Logger
from stk.util.tds import UncRepl
from stk.db.db_common import BaseDB
from stk.valf import PluginManager

# - defines -----------------------------------------------------------------------------------------------------------
# deprecated:
SDF_FILE_EXT = [".sdf"]
MAX_INT64 = 9223372036854775807


# - classes -----------------------------------------------------------------------------------------------------------
class DBConnect(object):
    """Class to establish connections with a database system"""

    def __init__(self,
                 dbq=None,
                 dsn=None,
                 user=None,
                 pw=None,
                 master=None,
                 drv=None,
                 tbl_prefix=None,
                 db_file=None,
                 error_tolerance=ERROR_TOLERANCE_NONE,
                 use_cx_oracle=None):
        """ Init DB Connector Class

            Supports:
              - Oracle DB Connections
              - SQLite3 DB Connections
              - SQL Server Compact Edition Connections

            :param dbq: deprecated: Database TSN (default: racadmpe)
            :param dsn: deprecated: User or System DSN registered on the local machine (default: CLEO)
            :param drv: deprecated: SQLCE driver
            :param user: Database User
            :type user: str
            :param pw: Password
            :type pw: str
            :param master: Master Schema Prefix  (i.e. DEV_ARS31x_ADMIN)
            :type master: str
            :param tbl_prefix: Table Prefix
            :type tbl_prefix: str
            :param db_file: Database File for SQLite3 Connections
            :type db_file: str
            :param error_tolerance: Error Tolerance for the DB interface
            :type error_tolerance: int
            :param use_cx_oracle: deprecated
        """
        self._dbfile = UncRepl().repl(db_file)
        self._dbprovider = None
        self._masterdbuser = user
        self._masterdbpassword = pw
        self._masterdbschemaprefix = master
        self._tableprefix = tbl_prefix
        self._logger = Logger(self.__class__.__name__)
        self._errortolerance = error_tolerance
        self._db_dir = abspath(join(dirname(currentframe().f_code.co_filename)))
        self._db = None
        self._conns = []

        self._preconnect()

    def __del__(self):
        """close db connection fully"""
        if self._db is not None:
            self._db.close()
            self._db = None

    def Connect(self, db_sub):  # pylint: disable=C0103
        """
        Connects to a DB system

        :param db_sub: Database object
        :type db_sub: object
        :return: DB connection
        :rtype: dbConnection
        """
        try:
            self._conns.append(self._GetMatchPlugInClass(PluginBaseDB, db_sub)(self._db.db_connection,
                                                                               error_tolerance=self._errortolerance))
            return self._conns[-1]
        except Exception, ex:
            self._logger.error("Could not initialize db connection due to '%s'" % str(ex))
            return None

    def DisConnect(self, dbConnection):  # pylint: disable=C0103
        """
        Terminates a connection to a DB system

        :param dbConnection: Database connection
        :type dbConnection: BaseDB
        """
        if dbConnection in self._conns:
            self._conns.remove(dbConnection)
            if not self._conns:
                self._db.close()
        else:
            self._logger.warning("Could not close db connection %s, it was closed before." % dbConnection)

    def _preconnect(self):
        """use BaseDB to preconnect one"""
        if self._dbfile is None:
            self._db = BaseDB("uid=%s;pwd=%s" % (self._masterdbuser, self._masterdbpassword),
                              table_prefix=GetFullTablePrefix(self._masterdbschemaprefix, self._tableprefix),
                              error_tolerance=self._errortolerance)

        elif not isfile(self._dbfile):
            self._logger.error("Database file '%s' does not exist." % self._dbfile)
            return -1
        else:
            self._db = BaseDB(self._dbfile,
                              table_prefix=GetFullTablePrefix(self._masterdbschemaprefix, self._tableprefix),
                              error_tolerance=self._errortolerance)

    def _GetMatchPlugInClass(self, cls, module):  # pylint: disable=C0103
        """ Return the plugin class supported by the given module

            :param cls: Class supporting the plugin
            :type cls: class
            :param module: Module containing the plugin class
            :type module: module
        """

        # get all folders to search
        plugin_folder_list = [folder_path for folder_path in list_folders(self._db_dir)]

        # find all modules implementing the plugin
        plugin_manager = PluginManager(plugin_folder_list, cls)
        plugin_list = plugin_manager.get_plugin_class_list(remove_duplicates=True)

        # match the plugin and the module
        for _, obj in getmembers(module):  # load all members of the given object
            if isclass(obj):  # if type class
                for plugin in plugin_list:  # compare with the supported plugins
                    if plugin['name'] == obj.__name__:  # if plugin found the object, open the connection
                        return obj
        return None


"""
CHANGE LOG:
-----------
$Log: db_connect.py  $
Revision 1.6 2016/08/16 12:26:22CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.5 2015/07/27 18:17:39CEST Hospes, Gerd-Joachim (uidv8815)
close only passed connection (mainly for Oracle)
- Added comments -  uidv8815 [Jul 27, 2015 6:17:39 PM CEST]
Change Package : 361396:1 http://mks-psad:7002/im/viewissue?selection=361396
Revision 1.4 2015/07/16 15:25:01CEST Ahmed, Zaheer (uidu7634)
minor bug fix to propagate error tolerance
--- Added comments ---  uidu7634 [Jul 16, 2015 3:25:02 PM CEST]
Change Package : 348978:2 http://mks-psad:7002/im/viewissue?selection=348978
Revision 1.3 2015/07/14 13:17:44CEST Mertens, Sven (uidv7805)
using preconnection to establish one connection
--- Added comments ---  uidv7805 [Jul 14, 2015 1:17:45 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/07/14 09:33:46CEST Mertens, Sven (uidv7805)
let connection build up by BaseDB
--- Added comments ---  uidv7805 [Jul 14, 2015 9:33:46 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:03:52CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
Revision 1.24 2015/03/13 09:18:37CET Mertens, Sven (uidv7805)
docu fix
--- Added comments ---  uidv7805 [Mar 13, 2015 9:18:37 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.23 2015/02/06 08:08:58CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:08:58 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.22 2015/01/30 10:34:53CET Mertens, Sven (uidv7805)
called via valfs DBConnector, but also can be used separatly,
therefore adding uncreplacer here as well
--- Added comments ---  uidv7805 [Jan 30, 2015 10:34:54 AM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.21 2014/11/11 09:56:13CET Mertens, Sven (uidv7805)
removing deprecation warning
Revision 1.20 2014/10/20 12:57:21CEST Ahmed, Zaheer (uidu7634)
pylint fixes. Added Sqlite3 adapter to handle unsigned 64bit integer
--- Added comments ---  uidu7634 [Oct 20, 2014 12:57:21 PM CEST]
Change Package : 267593:2 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.19 2014/10/09 14:34:22CEST Mertens, Sven (uidv7805)
moving to non-deprecated methods
--- Added comments ---  uidv7805 [Oct 9, 2014 2:34:24 PM CEST]
Change Package : 270435:1 http://mks-psad:7002/im/viewissue?selection=270435
Revision 1.18 2014/10/08 12:39:47CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 8, 2014 12:39:47 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.17 2014/10/07 14:07:09CEST Ellero, Stefano (uidw8660)
Improve epydoc documentation for the for stk.db.root subpakage.
--- Added comments ---  uidw8660 [Oct 7, 2014 2:07:09 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.16 2013/05/29 15:21:27CEST Raedler, Guenther (uidt9430)
- support cx oracle interface support
--- Added comments ---  uidt9430 [May 29, 2013 3:21:27 PM CEST]
Change Package : 184344:1 http://mks-psad:7002/im/viewissue?selection=184344
Revision 1.15 2013/04/19 13:32:04CEST Hecker, Robert (heckerr)
Functionality reverted to revision1.11.
--- Added comments ---  heckerr [Apr 19, 2013 1:32:04 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.14 2013/04/15 12:08:42CEST Mertens, Sven (uidv7805)
small bugfixes
--- Added comments ---  uidv7805 [Apr 15, 2013 12:08:43 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.13 2013/04/12 15:42:35CEST Mertens, Sven (uidv7805)
fix: missing self on own method call
--- Added comments ---  uidv7805 [Apr 12, 2013 3:42:35 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.12 2013/04/12 15:01:18CEST Mertens, Sven (uidv7805)
minor DB connection update due to VALF connection change
Revision 1.11 2013/04/03 08:02:16CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:17 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/27 13:51:25CET Mertens, Sven (uidv7805)
pylint: bugfixing and error reduction
--- Added comments ---  uidv7805 [Mar 27, 2013 1:51:26 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.9 2013/03/27 11:37:25CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
--- Added comments ---  uidv7805 [Mar 27, 2013 11:37:25 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/26 16:19:35CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:36 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/07 07:21:23CET Raedler, Guenther (uidt9430)
- removed some more pep8
--- Added comments ---  uidt9430 [Mar 7, 2013 7:21:23 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.6 2013/03/06 12:44:48CET Raedler, Guenther (uidt9430)
- changed exclipse settings to follow peps8
--- Added comments ---  uidt9430 [Mar 6, 2013 12:44:49 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.4 2013/03/04 07:47:32CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:33 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 13:59:46CET Hecker, Robert (heckerr)
Some changes regarding Pep8
--- Added comments ---  heckerr [Feb 27, 2013 1:59:47 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/26 16:23:25CET Raedler, Guenther (uidt9430)
- use only a single connection for the sqlite db
- add error tolerance to connector
--- Added comments ---  uidt9430 [Feb 26, 2013 4:23:25 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/19 14:08:42CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/project.pj
"""
