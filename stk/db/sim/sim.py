"""
stk/db/cat/cat.py
-------------------

Python library to access Simulation DB

Sub-Scheme SIM

**User-API**
    - `BaseSimulationDB`
        providing methods manage camera and radar sensor fusion data

The other classes in this module are handling the different DB types and are derived from BaseSimulationDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseSimulationDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseSimulationDB`.

:org:           Continental AG
:author:        Zaheer Ahmed

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:15CEST $
"""
# pylint: disable=W0702
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, ERROR_TOLERANCE_NONE, PluginBaseDB
from stk.db.db_sql import GenericSQLStatementFactory, SQLBinaryExpr, OP_EQ, OP_AND, SQLLiteral
from stk.db.cat.cat import TABLE_NAME_FILES, COL_NAME_FILES_MEASID, COL_NAME_FILES_FILEPATH
from stk.valf.signal_defs import DBSIM
from stk.util.helper import deprecated

# - defines -----------------------------------------------------------------------------------------------------------
# Table base names:
IDENT_STRING = DBSIM

TABLE_NAME_SIM_FILES = "SIM_FILES"
TABLE_NAME_SIM_TS_MAP = "SIM_TS_MAP"

# TABLE_NAME_SIM_FILES = "SIM_FILES"
COLUMN_NAME_SIM_FILES_SIMID = "SIMID"
COLUMN_NAME_SIM_FILES_MEASID_C1 = "MEASID_C1"
COLUMN_NAME_SIM_FILES_BINFILE_C1 = "BINFILE_C1"
COLUMN_NAME_SIM_FILES_MEASID_C2 = "MEASID_C2"
COLUMN_NAME_SIM_FILES_START_TS = "START_TS"
COLUMN_NAME_SIM_FILES_END_TS = "END_TS"
# SQLITE SPECIFIC
COLUMN_NAME_SIM_FILES_RECFILE_C2 = "RECFILE_C2"

# TABLE_NAME_SIM_TS_MAP = "SIM_TS_MAP"
COLUMN_NAME_SIM_TS_MAP_MEASID_C1 = "MEASID_C1"
COLUMN_NAME_SIM_TS_MAP_ETH_TS = "ETH_TS"
COLUMN_NAME_SIM_TS_MAP_RTE_TS = "RTE_TS"

DBSIM_SUB_SCHEME_TAG = "SIM"


# - classes -----------------------------------------------------------------------------------------------------------
class BaseSimulationDB(BaseDB):  # pylint: disable=R0904
    """
    **base class provide interface to SIM subschema**
    which is used for camera and radar sensor fusion

    For the first connection to the DB for sim tables just create a new instance of this class like

    .. python::

        from stk.db.sim.sim import BaseSimulationDB

        dbsim = BaseSimulationDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbsim = BaseSimulationDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    More optional keywords are described at `BaseDB` class initialization.

    """
    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseSimulationDB to represent SIM subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        """
        kwargs['strIdent'] = DBSIM
        BaseDB.__init__(self, *args, **kwargs)

    def get_sim_file(self, simfile_id=None, measid_c1=None, binfile_c1=None, measid_c2=None):
        """
        Get list of record based from SIM_FILES table

        :param simfile_id: simulation id i.e. primary key value
        :type simfile_id: int
        :param measid_c1: Measurement ID for the camera recording
        :type measid_c1: int
        :param binfile_c1: Bsig File path corresponding to camera recording
        :type binfile_c1: str
        :param measid_c2: Measurement ID for the radar recording
        :type measid_c2: int
        :return: Record fetched from database
        :rtype: list
        """
        cond = self._sim_file_condition(simfile_id=simfile_id, measid_c1=measid_c1,
                                        binfile_c1=binfile_c1, measid_c2=measid_c2)
        entries = self.select_generic_data(table_list=[TABLE_NAME_SIM_FILES], where=cond)
        for entry in entries:
            entry[COLUMN_NAME_SIM_FILES_RECFILE_C2] = self._get_rec_filepath(entry[COLUMN_NAME_SIM_FILES_MEASID_C2])
        return entries

    def delete_sim_file(self, simfile_id=None, measid_c1=None, binfile_c1=None, measid_c2=None):
        """
        Delete data from SIM_FILE table based criterea of pass argument

        :param simfile_id: simulation id i.e. primary key value
        :type simfile_id: int
        :param measid_c1: Measurement ID for the camera recording
        :type measid_c1: int
        :param binfile_c1: Bsig File path corresponding to camera recording
        :type binfile_c1: str
        :param measid_c2: Measurement ID for the radar recording
        :type measid_c2: int
        """
        cond = self._sim_file_condition(simfile_id=simfile_id, measid_c1=measid_c1,
                                        binfile_c1=binfile_c1, measid_c2=measid_c2)

        self.delete_generic_data(TABLE_NAME_SIM_FILES, where=cond)

    def add_sim_file(self, record, check_filepath=True):
        """
        Add Sim File record into database

        :param record: record to be insert
        :type record: dict
        :param check_filepath: Flag to verify recfile corresponds to measid
        """
        if COLUMN_NAME_SIM_FILES_RECFILE_C2 in record:
            recfile_c2 = record[COLUMN_NAME_SIM_FILES_RECFILE_C2]
            record.pop(COLUMN_NAME_SIM_FILES_RECFILE_C2)
        else:
            recfile_c2 = ""

        if COLUMN_NAME_SIM_FILES_BINFILE_C1 in record:
            record[COLUMN_NAME_SIM_FILES_BINFILE_C1] = record[COLUMN_NAME_SIM_FILES_BINFILE_C1].lower()

        if check_filepath:
            if recfile_c2.lower() == self._get_rec_filepath(record[COLUMN_NAME_SIM_FILES_MEASID_C2]):
                self.add_generic_data(record, TABLE_NAME_SIM_FILES)
            else:
                raise StandardError("The recfile path doesn't correspond of measid")
        else:
            self.add_generic_data(record, TABLE_NAME_SIM_FILES)

    def _get_rec_filepath(self, measid_c2):
        """
        Function use to verify if the measurement Id
        really correspond recfile path

        :param measid_c2: Measurement Id
        :type measid_c2: int
        :return: File path of recording
        :rtype: StringSQLBinaryExpression
        """

        cond = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measid_c2)
        entries = self.select_generic_data(select_list=[COL_NAME_FILES_FILEPATH], table_list=[TABLE_NAME_FILES],
                                           where=cond)
        if len(entries) == 1:
            measid = entries[0][COL_NAME_FILES_FILEPATH].lower()
            return measid
        else:
            return None

    @staticmethod
    def _sim_file_condition(simfile_id=None, measid_c1=None, binfile_c1=None, measid_c2=None):
        """
        Generic function for creating SQL Condition for SIM_FILE

        :param simfile_id: simulation id i.e. primary key value
        :type simfile_id: int
        :param measid_c1: Measurement ID for the camera recording
        :type measid_c1: int
        :param binfile_c1: Bsig File path corresponding to camera recording
        :type binfile_c1: str
        :param measid_c2: Measurement ID for the radar recording
        :type measid_c2: int
        """

        cond = None
        if simfile_id is not None:
            cond = SQLBinaryExpr(COLUMN_NAME_SIM_FILES_SIMID, OP_EQ, simfile_id)

        if measid_c1 is not None:
            if cond is None:
                cond = SQLBinaryExpr(COLUMN_NAME_SIM_FILES_MEASID_C1, OP_EQ, measid_c1)
            else:
                cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COLUMN_NAME_SIM_FILES_MEASID_C1, OP_EQ, measid_c1))

        if binfile_c1 is not None:
            if cond is None:
                cond = SQLBinaryExpr(COLUMN_NAME_SIM_FILES_BINFILE_C1, OP_EQ, SQLLiteral(binfile_c1.lower()))
            else:
                cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COLUMN_NAME_SIM_FILES_BINFILE_C1,
                                                                 OP_EQ, SQLLiteral(binfile_c1.lower())))

        if measid_c2 is not None:
            if cond is None:
                cond = SQLBinaryExpr(COLUMN_NAME_SIM_FILES_MEASID_C2, OP_EQ, measid_c2)
            else:
                cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COLUMN_NAME_SIM_FILES_MEASID_C2, OP_EQ, measid_c2))
        return cond

    def add_sim_time_stamp_map(self, record):
        """
        Add Simulation TimeStamp map RTE and RTH for measurement

        :param record:
        :type record:
        """
        self.add_generic_data(record, TABLE_NAME_SIM_TS_MAP)

    def get_sim_time_stamp_map(self, measid_c1):
        """
        Get Simulation TimeStamp map RTE and RTH for measurement

        :param measid_c1:
        :type measid_c1:
        """
        cond = self._sim_file_condition(measid_c1=measid_c1)
        return self.select_generic_data(table_list=[TABLE_NAME_SIM_TS_MAP], where=cond)

    def delete_sim_time_stamp_map(self, measid_c1):
        """
        Delete Simulation TimeStamp map RTE and RTH for measurement

        :param measid_c1:
        :type measid_c1:
        """
        cond = self._sim_file_condition(measid_c1=measid_c1)
        self.delete_generic_data(TABLE_NAME_SIM_TS_MAP, where=cond)

    # ====================================================================
    # deprecated methods
    # ====================================================================

    @deprecated('get_sim_file')
    def GetSimFile(self, simfile_id=None, measid_c1=None,  # pylint: disable=C0103
                   binfile_c1=None, measid_c2=None):
        """deprecated"""
        return self.get_sim_file(simfile_id, measid_c1, binfile_c1, measid_c2)

    @deprecated('add_sim_file')
    def AddSimFile(self, record, check_filepath=True):  # pylint: disable=C0103
        """deprecated"""
        return self.add_sim_file(record, check_filepath)

    @deprecated('delete_sim_file')
    def DeleteSimFile(self, simfile_id=None, measid_c1=None,  # pylint: disable=C0103
                      binfile_c1=None, measid_c2=None):
        """deprecated"""
        return self.delete_sim_file(simfile_id, measid_c1, binfile_c1, measid_c2)

    @deprecated('get_sim_time_stamp_map')
    def GetSimTimeStampMap(self, measid_c1):  # pylint: disable=C0103
        """deprecated"""
        return self.get_sim_time_stamp_map(measid_c1)

    @deprecated('add_sim_time_stamp_map')
    def AddSimTimeStampMap(self, record):  # pylint: disable=C0103
        """deprecated"""
        return self.add_sim_time_stamp_map(record)

    @deprecated('delete_sim_time_stamp_map')
    def DeleteSimTimeStampMap(self, measid_c1):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_sim_time_stamp_map(measid_c1)


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginSimDB(BaseSimulationDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseSimulationDB.__init__(self, *args, **kwargs)


class SQLCESimulationDB(BaseSimulationDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseSimulationDB.__init__(self, *args, **kwargs)


class OracleSimulationDB(BaseSimulationDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseSimulationDB.__init__(self, *args, **kwargs)


class SQLite3SimulationDB(BaseSimulationDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseSimulationDB.__init__(self, *args, **kwargs)


"""
CHANGE LOG:
-----------
$Log: sim.py  $
Revision 1.5 2016/08/16 12:26:15CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.4 2015/07/14 13:20:59CEST Mertens, Sven (uidv7805)
reverting some changes
- Added comments -  uidv7805 [Jul 14, 2015 1:20:59 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.3 2015/07/14 09:32:15CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:32:16 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/04/30 11:09:30CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:31 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:20CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/sim/project.pj
Revision 1.7 2015/04/27 14:34:43CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:34:43 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.6 2015/03/09 11:52:15CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:16 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.5 2015/03/05 14:22:05CET Mertens, Sven (uidv7805)
adaptation for parameters
--- Added comments ---  uidv7805 [Mar 5, 2015 2:22:05 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.4 2014/12/09 12:43:45CET Mertens, Sven (uidv7805)
removing unneeded init call
--- Added comments ---  uidv7805 [Dec 9, 2014 12:43:46 PM CET]
Change Package : 281276:1 http://mks-psad:7002/im/viewissue?selection=281276
Revision 1.3 2014/11/17 09:56:28CET Mertens, Sven (uidv7805)
namings alignment
--- Added comments ---  uidv7805 [Nov 17, 2014 9:56:28 AM CET]
Change Package : 281272:1 http://mks-psad:7002/im/viewissue?selection=281272
Revision 1.2 2014/08/06 10:02:24CEST Hecker, Robert (heckerr)
updated to new naming convensions.
--- Added comments ---  heckerr [Aug 6, 2014 10:02:25 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.1 2014/07/04 10:29:55CEST Ahmed, Zaheer (uidu7634)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/sim/project.pj
"""
