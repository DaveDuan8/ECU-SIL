"""
example_observer
----------------

TODO: document your observer

:org:           Continental AG
:author:        uidx0815

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 20:56:43CET $
"""

# Import Python Modules -----------------------------------------------------------------------------------------------
from framework.valf.base_component_ifc import BaseComponentInterface as bci


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
        """
        # noinspection PyCallByClass,PyTypeChecker
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.1 $")

        self._db_connections = None
        self._reccat_db = None
        self._objdata_db = None
        self._genlbl_db = None
        self._gbl_db = None
        self._valres_db = None

    def initialize(self):
        """Initialize methods are called for all observers in configured order
        """
        # call debug any you'll see that your Initialize has been called inside log
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def post_initialize(self):
        """PostInitialize methods are called for all observers in configured order after all Initialize's done
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def load_data(self):
        """
        first method of the loop (LoadData -> ProcessData -> PostProcessData),
        this loop is repeated by the ProcessManager until data port 'IsFinished' is set to True

        e.g. using the CollectionReader it will run for each simulation output file of the collection/bpl file

        you can start loading your data here
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def process_data(self):
        """
        this method is also part of the loop through all sim output files

        here, data can be processed
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def post_process_data(self):
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

    def pre_terminate(self):
        """called after all files are processed (LoadData -> ProcessData -> PostProcessData)
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK

    def terminate(self):
        """called as last, do any missing things, like closing files, DB, etc.
        """
        self._logger.debug()

        # TODO: add your code here

        return bci.RET_VAL_OK


"""
$Log: example_observer.py  $
Revision 1.1 2020/03/25 20:56:43CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/test_cases/project.pj
"""
