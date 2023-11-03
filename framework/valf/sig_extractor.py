"""
sig_extractor2
--------------
Custom implementation of the signal extractor.
Instead of loading list of lists of lists this one loads object lists
into a list of AlgoObjects, the list is actually a AlgoObjectContainer
to let room for extension later on.

More on the implementation:
All other signal are loaded into a single Dataframe so that each signal
has an exact relation to one timestamp. This will ease comparing a lot.
As the signal list the AlgoObjectContainer has also a single dataframe for
all objects, this allows for deeper analysis.

A sample configuration is given below:
::
    ("PdSignalExtractor", {

        "aSignalBlock": {
            "Prefix": "MTS.Package.",
            "Mapping": [
                {"path": "TimeStamp",
                "name": "TimeStamp"},
                {"path": "CycleCount",
                "name": "CycleCount"},
             ],
        },

        "aSignalListBlock": {
            "Prefix": "SIM VFB ALL.AlgoSenCycle.gSI_OOI_LIST.SI_OOI_LIST[{0:}].",
            "ListSize": 6,
            "Mapping": [
            {"path": "object_id",
             "name": "object_id_{0:}"},
            {"path": "long_displacement",
             "name": "long_displacement_{0:}"},
            ],
        },

        "ObjectList": {
            "ListSize": 100,
            "MinLifeTime": 10,
            "SignalBase": "SIM VFB ALL.DataProcCycle.EMPublicObjData.Objects[{0:}].",
            "SignalProperties": [
                {"path": "Kinematic.fDistX", "name": "DistX"},
                {"path": "Kinematic.fDistY", "name": "DistY"},
            ]
        },

        })

Each SignalBlock entry has to be unique, because this name is used to publish
the extracted dataframe on the bus. The simplest configuration is named
'aSignalBlock' in the configuration shown above. In the mapping part any
number of signals can be defined. The path is the fullname, or if the prefix
item is used, the last part of the signal name in the BSIG file. The name item
is used as the column name in the dataframe and hence has to be unique.
All signal are exported into a single dataframe per signal block item.

Are more complex option is the shown in the second block. The additional
ListSize item is used to iterated over signal arrays starting from 0 and ending
with ListSize - 1.

For object list extracting the ObjectList block can be configured.
"""
from __future__ import print_function

import numpy as np
import pandas as pd

from framework.io.signalreader import SignalReader
from framework.valf.base_component_ifc import BaseComponentInterface

MIN_LIFE_TIME = "MinLifeTime"
SIGNAL_PROPERTIES = "SignalProperties"
SIGNAL_BASE = "SignalBase"
TIME_STAMP = "TimeStamp"
MTS = "MTS"
SIG_NAME = "name"
PATH = "path"
PREFIX = "Prefix"
SYNC_TIMESTAMP = "SyncTimestamp"
DTYPE = "dtype"
MAPPING = "Mapping"
LIST_SIZE = "ListSize"
MTS_TIME_STAMP = "MTS.Package.TimeStamp"
OBJECT_LIST = "ObjectList"
OOI_LIST = "OOIList"
SIMFILE = "currentsimfile"
CFG_KEY = "PdSignalExtractor"
# SIGNALS = "pd_signals"
PORT_OBJ_LIST = "pd_obj_list"

__author__ = "Philipp Baust"
__copyright__ = "Copyright 2014, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 21:38:09CET $"


class PdSignalExtractor(BaseComponentInterface):
    """ Observer that is able to extract signals and object list from an
        BSIG file. The extracted signals and object list can be configured
        in the ValF configuration.
    """
    def __init__(self, data_manager, component_name, bus_name):
        """ Initialized the observer.
            :param data_manager: Datamanager to access the bus.
            :param component_name: The component name
            :param bus_name: list of the connected buses
        """
        BaseComponentInterface.__init__(self, data_manager, component_name,
                                        bus_name)

        self._config = None
        self.bsig_reader = None

    def initialize(self):
        """ Receives the configuration from the bus. """
        self._config = self._data_manager.get_data_port(CFG_KEY, self._bus_name)

        if not self._config:
            self._logger.error("Missing config '{}'. Please check your config"
                               .format(CFG_KEY))
            return self.RET_VAL_ERROR

        return self.RET_VAL_OK

    def load_data(self):
        """ Performs the signal extraction. The signalblock and object lists
            are published to the connected bus.
        """
        # self.bsig_reader = BsigReader()
        bsig_file = self._data_manager.get_data_port(SIMFILE, self._bus_name)
        if bsig_file is None:
            raise Exception("Configuration must be wrong, received no bsig")
        # self.bsig_reader.open(bsig_file)
        self.bsig_reader = SignalReader(bsig_file, delim=",")

        # All other blocks, one data frame per block
        for key in self._config:
            if key not in [OBJECT_LIST, ]:
                self._load_block(key)

        self.bsig_reader.close()
        return self.RET_VAL_OK

    def _load_block(self, key):
        """  Performs the loading of signals per config block.  """
        self._logger.debug("Loading signals from bsig into {0:} data frame"
                           .format(key))
        cfg = self._config[key]

        mts_ts_name = MTS_TIME_STAMP
        mts_ts_dtype = np.long
        # raw_ts_signal = self.bsig_reader.get_signal_by_name(mts_ts_name)
        raw_ts_signal = self.bsig_reader[mts_ts_name]
        ts_signal = np.fromiter(raw_ts_signal, mts_ts_dtype)

        if LIST_SIZE in cfg:
            self._logger.debug("Loading signal list for block {0:}".format(key))

            signals = pd.DataFrame(index=ts_signal)
            for k in range(cfg[LIST_SIZE]):
                for desc in cfg[MAPPING]:
                    full_path = (cfg[PREFIX] + desc[PATH]).format(k)
                    column_name = desc[SIG_NAME].format(k)
                    self._logger.debug("Loading: {0:} as {1:}"
                                       .format(full_path, column_name))

                    # raw_signal = self.bsig_reader.get_signal_by_name(full_path)
                    raw_signal = self.bsig_reader[full_path]
                    signal = np.fromiter(raw_signal, np.float64)
                    signals[column_name] = pd.Series(signal, signals.index)

            self._data_manager.set_data_port(key, signals, self._bus_name)

        else:
            self._logger.debug("Loading signals for block {0:}".format(key))

            signals = pd.DataFrame(index=ts_signal)
            for desc in cfg[MAPPING]:
                full_path = cfg[PREFIX] + desc[PATH]
                column_name = desc[SIG_NAME]
                self._logger.debug("Loading: {0:} as {1:}"
                                   .format(full_path, column_name))

                # raw_signal = self.bsig_reader.get_signal_by_name(full_path)
                raw_signal = self.bsig_reader[full_path]

                if DTYPE in desc.keys():
                    value = desc[DTYPE]
                    type_ = getattr(np, value)
                    dtype = type_
                else:
                    dtype = np.float

                signal = np.fromiter(raw_signal, dtype)
                signals[column_name] = pd.Series(signal, signals.index)

            self._data_manager.set_data_port(key, signals, self._bus_name)

    def process_data(self):
        # self._logger.debug("Selftest")

        # df = self._data_manager.get_data_port(SIGNALS, self._bus_name)
        # self._logger.debug(df.describe())

        # df = self._data_manager.get_data_port("VDY", self._bus_name)
        # self._logger.debug("\n" + str(df.describe()))
        pass

"""
CHANGE LOG:
-----------
$Log: sig_extractor.py  $
Revision 1.1 2020/03/25 21:38:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""