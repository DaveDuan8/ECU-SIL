"""
example_observer
----------------

TODO: document your observer

:org:           Continental AG
:author:        uidx0815

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/04/12 15:05:00CEST $
"""

# Import Python Modules -----------------------------------------------------------------------------------------------
from os import path as opath
from sys import path as spath

# Import STK Modules --------------------------------------------------------------------------------------------------
STKDIR = opath.abspath(r"..\..\..")
if STKDIR not in spath:
    spath.append(STKDIR)

from stk.valf.base_component_ifc import BaseComponentInterface as bci
from stk.valf.signal_defs import DATABASE_OBJECTS_PORT_NAME


# Classes -------------------------------------------------------------------------------------------------------------
class ExampleObserver(bci):
    """TODO: explain what your observer should do or is doing
    """
    def __init__(self, data_manager, component_name, bus_name):
        """standard observers are instanciated with those
        this is standard init from python

        :param data_manager: data manager in use (self._data_manager)
        :param component_name: name of component as stated in config (self._component_name)
        :param bus_name: name of bus to use as stated in config (self._bus_name)
        :param rev: revision of mine (self._version)
        """
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.3 $")

        self._logger.debug()

        self._db_connections = None
        self._reccat_db = None
        self._objdata_db = None
        self._genlbl_db = None
        self._gbl_db = None
        self._valres_db = None

    def Initialize(self):
        """Initialize methods are called for all observers in configured order
        """
        # call debug any you'll see that your Initialize has been called inside log
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def PostInitialize(self):
        """PostInitialize methods are called for all observers in configured order after all Initialize's done
        """
        self._logger.debug()

        # Get the database connection
        self._db_connections = self._get_data(DATABASE_OBJECTS_PORT_NAME, self._get_data('dbbus', default="DBBus#1"))
        if self._db_connections:
            self._reccat_db = self._db_connections.get('cat', None)
            self._objdata_db = self._db_connections.get('obj', None)
            self._genlbl_db = self._db_connections.get('lbl', None)
            self._gbl_db = self._db_connections.get('gbl', None)
            self._valres_db = self._db_connections.get('val', None)

        if self._reccat_db is None:
            self._logger.warning("Database connection to recfile catalogue could not be established")
        if self._objdata_db is None:
            self._logger.warning("Database connection to object data could not be established")
        if self._genlbl_db is None:
            self._logger.warning("Database connection to generic label data could not be established")
        if self._gbl_db is None:
            self._logger.warning("Database connection to global data could not be established")
        if self._valres_db is None:
            self._logger.warning("Database connection to validation results data could not be established")

        # TODO: add your code here

        return bci.RET_VAL_OK

    def LoadData(self):
        """
        first method of the loop (LoadData -> ProcessData -> PostProcessData),
        this loop is repeated by the ProcessManager until data port 'IsFinished' is set to True

        e.g. using the CollectionReader it will run for each simulation output file of the collection/bpl file

        you can start loading your data here
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def ProcessData(self):
        """
        this method is also part of the loop through all sim output files

        here, data can be processed
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def PostProcessData(self):
        """
        last method of the loop through all sim output files,
        next method will be PreTerminate if port 'IsFinished' is set to True,
        otherwise it starts again with LoadData

        here, steps to post-process any open operations from ProcessData
        like cleaning up for the next simulation output file
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def PreTerminate(self):
        """called after all files are processed (LoadData -> ProcessData -> PostProcessData)
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def Terminate(self):
        """called as last, do any missing things, like closing files, DB, etc.
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK


"""
$Log: example_observer.py  $
Revision 1.3 2016/04/12 15:05:00CEST Hospes, Gerd-Joachim (uidv8815) 
fix docu during result saver implementation
Revision 1.2 2015/07/03 16:03:48CEST Hospes, Gerd-Joachim (uidv8815)
change to db_linker, extend some comments
- Added comments -  uidv8815 [Jul 3, 2015 4:03:48 PM CEST]
Change Package : 353608:1 http://mks-psad:7002/im/viewissue?selection=353608
Revision 1.1 2015/04/23 19:05:52CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
Revision 1.2 2015/02/26 16:16:36CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Feb 26, 2015 4:16:37 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.1 2014/09/23 13:26:11CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/valf/obs/project.pj
"""
