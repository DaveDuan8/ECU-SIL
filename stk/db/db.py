"""
stk/db/db
---------

Base DB Module, which contain some Bases Classes to communicate with different
Database Systems.

Content:
--------

    - `DBBase` Base Db Class, for handling basic and interface specific methods.
    - `DBGeneric` Base class for all further DB-Interface classes.
    - `Odbc` Interface class for DB access via ODBC.
    - `SQLite` Interface class for DB via SQLite3.
    - `Oracle` Interface class for DB via cx_Oracle (native).
    - `SqlCE` Interface class for DB via adodbapi.

usage
-----
.. python::

    from stk.db.db import Odbc
    from stk.db.db import SQLite

    # Example Code How to use the ClDB
    #Create a Instance of the ClDB with ODBC Interface
    cl = ClDB(SQLite())
    cl.connect("MyConnectionString")
    cl.SigConstraintDB.add(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    cl.SigConstraintDB.commit()

    # Or
    odbc = Odbc()
    odbc.connect('dsn', 'dbq', 'uid', 'pwd', 'driver')
    cl = ClDB(odbc)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:39CEST $
"""

# Import Python Modules -------------------------------------------------------
import sqlite3  # Needed for Native SQLite DB Access
import pyodbc  # Needed for Database Access over ODBC
import cx_Oracle  # Needed for Native Oracle DB Access
import adodbapi  # Needed for SqlCE DataBase

# Import STK Modules --------------------------------------------------------------------------------------------------

# Defines -------------------------------------------------------------------------------------------------------------
DEFAULT_MASTER_DRV_XP = "Oracle in instantclient11_1"  # Released for WinXP
DEFAULT_MASTER_DRV = "Oracle in instantclient_11_2"  # Released for Win7

# Classes -------------------------------------------------------------------------------------------------------------


class DBGeneric(object):
    """
    Generic DB Class which must be used as Base class for every DB-Interface implementation.
    This Base class offers the basic methods for connection, qery's, selects....

    :author:        Robert Hecker
    :date:          12.04.2013
    """
    def __init__(self, dbifc):
        """
        Standard Constructor for the DBGeneric class.
        Here the Initialization for the DB Interface is done.

        Supported classes for the dbifc are:

        - `Odbc` Interface class for DB access via ODBC.
        - `SQLite` Interface class for DB via SQLite3.
        - `Oracle` Interface class for DB via cx_Oracle (native).
        - `SqlCE` Interface class for DB via adodbapi.

        :param dbifc: Interface class, which must be used for the DB-Ifc-Connection.
        :type  dbifc: class
        :note:              Please Check the whole list for valid
        :author:        Robert Hecker
        :date:          12.04.2013
        """
        self._dbifc = dbifc
        self.db_type = dbifc.db_type

    def connect(self, connection_string):
        """
        Method to connect to the specified DB.
        The connection string is depending from the choosen DB Type.
        Please see the DB Interface classes for more details.

        :param connection_string: Connection String needed by the DB.
        :type  connection_string: string

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._dbifc.connect2(connection_string)

    def cursor(self):
        """
        Method to get the cursor object from the given connection.

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._dbifc.cursor()

    def commit(self):
        """
        Commit the changes into the DB

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._dbifc.commit()

    def rollback(self):
        """
        Rollback the changes from the DB to the last commit

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._dbifc.rollback()

    def close(self):
        """
        Close the DB Connection

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._dbifc.close()

    def execute(self, statement):
        """
        Execute a simple Statement.

        :author:        Robert Hecker
        :date:          12.04.2013
        :param statement: SQL query, supported statements: select, insert, update, delete, execute
        :type statement: String
        :return: returns all rows
        """
        return self._dbifc.execute(statement)


class DBBase(object):
    """
    Base DB Class, which takes care for basic functionality and the mapping for
    calling methods from the given Interface classes. (e.g. Odbc())

    :author:        Robert Hecker
    :date:          20.02.2013
    """
    def __init__(self, db_type="Unknown"):
        self._cxcn = None
        self.db_type = db_type

    def connect(self, connection_string):
        """
        Custom connect Method to connect to a DB System with multiple Arguments
        Must be overridden by the real DB-Interface Method.

        :param connection_string: Connection string to a DB System
        :type connection_string: String

        """
        pass

    def connect2(self, connection_string):
        """
        Custom connect2 Method, to connect to a DB System with a single Connection
        String. Must be overridden by the REal DB-Interface Method.

        :param connection_string: Connection string to a DB System
        :type connection_string: String

        """
        pass

    def cursor(self):
        """
        Method to get the cursor object from the given connection.

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        return self._cxcn.cursor()

    def commit(self):
        """
        Commit the changes into the DB

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        self._cxcn.commit()

    def rollback(self):
        """
        Rollback the changes from the DB to the last commit

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        self._cxcn.rollback()

    def close(self):
        """
        Close the DB Connection

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        self._cxcn.close()

    def execute(self, statement):
        """Execute SQL statement(s). Multiple statements can be semicolon (;) separated
        :param statement: SQL query
        :type statement: String
        :return: returns all rows
        """
        cur = self.cursor()
        cur.execute(statement)
        cur.close()


class Odbc(DBBase):
    """
    Odbc Interface class, needed, when you want to connect to a DB via the
    ODBC-Driver.
    To be able to get a Database connection working with this class, you have
    to garantee, that following Drivers are installed:

    - odbc (Already included in Python(x,y)
    - ODBC Driver for your OS (with the correct connection settings

    :author:        Robert Hecker
    :date:          20.02.2013
    """
    def __init__(self):
        DBBase.__init__(self, "oracle")

    def connect(self, uid='DEV_ARS31X_PWRUSER_GT', pwd='ARS31X_PWRUSER_GT',
                dsn='CLEO', dbq='racadmpe',):
        """
        Method to connect to a ODBC DB.

        :param uid: User Id used to connect.
        :type  uid: string
        :param pwd: Password used to connect.
        :type  pwd: string
        :param dsn: DSN (Data Source Name) for the DB.
        :type  dsn: string
        :param dbq: DBQ (TNS Service Name) for the DB.
        :type  dbq: string

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        cns = ""
        if dsn is not None:
            cns = "DSN=%s;" % dsn
        else:
            cns = "DRIVER={%s};" % DEFAULT_MASTER_DRV
        if dbq is not None:
            cns = cns + "DBQ=%s;" % dbq
        if uid is not None:
            cns = cns + "Uid=%s;" % uid
        if pwd is not None:
            cns = cns + "Pwd=%s;" % pwd

        self.connect2(cns)

    def connect2(self, connectionString):
        """

        Custom connect2 Method, to connect to a DB System (ODBC) with a single Connection
        String.

        :param connectionString: Connection string
        :type connectionString: String

        """
        self._cxcn = pyodbc.connect(connectionString)


class Oracle(DBBase):
    """
    Oracle Interface class, which need to communicate to a
    Oracle Database with the native Interface.
    To be able to get a Database connection working with this class, you have
    to garantee, that following Drivers are installed:

    - cx_Oracle Package
    - Oracle Instant Client

    see also Needed Tools wiki page


    :author:        Robert Hecker
    :date:          20.02.2013
    """
    def __init__(self):
        DBBase.__init__(self, "oracle")

    def connect(self, uid='DEV_ARS31X_PWRUSER_GT', pwd='ARS31X_PWRUSER_GT',
                dbq='racadmpe'):
        """
        Method to connect to a Oracle DB.

        :param uid: User Id used to connect.
        :type  uid: string
        :param pwd: Password used to connect.
        :type  pwd: string
        :param dbq: DBQ (TNS Service Name) for the DB.
        :type  dbq: string

        :author:        Robert Hecker
        :date:          12.04.2013
        """
        cns = uid + '/' + pwd + '@' + dbq
        self.connect2(cns)

    def connect2(self, connectionString):
        """
        Custom connect2 Method, to connect to a DB System (Oracle) with a single Connection String.

        :param connectionString: Connection string to a DB System (Oracle)
        :type connectionString: String
        :return: Returns a connection to the Oracle DB specified in the connection string
        :rtype: cx_Oracle Connection object

        """

        self._cxcn = cx_Oracle.Connection(connectionString)


class SQLite(DBBase):
    """
    SQLite Interface class, which need to communicate to a SQLite3 Database
    with the native Interface.
    To be able to get a Database connection working with this class, you have
    to guarantee, that following Drivers are installed:

    - python sqlite3 Package (Already included in Python(x, y)

    :author:        Robert Hecker
    :date:          20.02.2013
    """
    def __init__(self):
        DBBase.__init__(self, "sqlite")

    def connect(self, database=r'c:\tmp.db'):
        """
        Custom connect Method, to connect to a SQLite DB.

        :param database: Connection string to a SQLite DB
        :type database: String
        :return: Returns a connection to the SQLite DB specified in the connection string
        :rtype: sqlite3 connection object

        """

        self.connect2(database)

    def connect2(self, database):
        """
        Custom connect2 Method, to connect to a SQLite DB.

        :param database: Connection string to a SQLite DB
        :type database: String
        :return: Returns a connection to the SQLite DB specified in the connection string
        :rtype: sqlite3 connection object

        """

        self._cxcn = sqlite3.connect(database)


class SqlCE(DBBase):
    """
    SqlCE Interface class, which is need to communicate to a Microsoft
    SQL Server Compact Database with the native Interface.

    :author:        Robert Hecker
    :date:          20.02.2013
    """
    def __init__(self):
        DBBase.__init__(self, "sqlce")

    def connect(self, database):
        """
        Custom connect Method, to connect to a Microsoft SQL Server Compact DB.

        :param database: Connection string to a Microsoft SQL Server Compact
        :type database: String
        :return: Returns a connection to the Microsoft SQL Server Compact specified in the connection string
        :rtype: ADOdb connection object

        """

        self.connect2(database)

    def connect2(self, database):
        """
        Custom connect2 Method, to connect to a Microsoft SQL Server Compact DB.

        :param database: Connection string to a Microsoft SQL Server Compact
        :type database: String
        :return: Returns a connection to the Microsoft SQL Server Compact specified in the connection string
        :rtype: ADOdb connection object

        """

        self._cxcn = adodbapi.connect(database)


"""
CHANGE LOG:
-----------
$Log: db.py  $
Revision 1.2 2016/08/16 16:01:39CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.1 2015/04/23 19:03:54CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
Revision 1.12 2014/10/08 12:40:16CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 8, 2014 12:40:16 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.11 2014/10/07 14:29:50CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 7, 2014 2:29:50 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.10 2013/04/16 19:26:23CEST Hecker, Robert (heckerr)
Changed from odbc module to pyodbc.
--- Added comments ---  heckerr [Apr 16, 2013 7:26:24 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/04/16 13:26:40CEST Hecker, Robert (heckerr)
Added doxygen docu.
--- Added comments ---  heckerr [Apr 16, 2013 1:26:40 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/04/15 12:31:30CEST Mertens, Sven (uidv7805)
fix for last unitTest
--- Added comments ---  uidv7805 [Apr 15, 2013 12:31:30 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.7 2013/04/15 12:08:41CEST Mertens, Sven (uidv7805)
small bugfixes
--- Added comments ---  uidv7805 [Apr 15, 2013 12:08:41 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.6 2013/03/22 08:24:24CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:25 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/20 18:22:16CET Hecker, Robert (heckerr)
Removed too long line.
--- Added comments ---  heckerr [Mar 20, 2013 6:22:16 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.4 2013/03/20 17:32:00CET Hecker, Robert (heckerr)
Simplified DB Interfaces.
--- Added comments ---  heckerr [Mar 20, 2013 5:32:00 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.3 2013/02/27 13:59:48CET Hecker, Robert (heckerr)
Some changes regarding Pep8
--- Added comments ---  heckerr [Feb 27, 2013 1:59:48 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/26 18:32:19CET Hecker, Robert (heckerr)
Get Interface Classes working with Unit Test.
--- Added comments ---  heckerr [Feb 26, 2013 6:32:19 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/26 14:00:58CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/db/project.pj
"""
