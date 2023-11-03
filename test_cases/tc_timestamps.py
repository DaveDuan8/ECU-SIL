"""
crt.ecu_sil.tc_timestamps
-------------------------
This module contains an ECU-SIL test case to check the availability of
all MTS timestamps and implicit all cycles. The test is used to check that
 the export from MTS is configured properly.
"""
from __future__ import print_function

import os
import numpy as np
import pandas as pd

from framework.util.gbl_defs import GblUnits
from framework.img.viz import AlgoSignal
from framework.val.asmt import ValAssessmentStates
from framework.val.results import ValTestStep
from tc_common import BaseTest
from tc_event_signals import EXP_RES
from tc_event_signals import MTS_PACKAGE_TIME_STAMP


__author__ = "Philipp Baust"
__copyright__ = "Copyright 2014, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 20:56:45CET $"


class TimestampTestcase(BaseTest):
    """ Test of timestamp availability. """

    def __init__(self, data_manager, testcase, config):
        """ Initializes the object. """
        BaseTest.__init__(self, data_manager, testcase, config)

        self.nan_count_60 = 0
        self.nan_count_20 = 0
        self.results_60 = None

    def calc_nan_values(self, ecu_ts, sil_ts):
        self._logger.debug("Signal vector length (ECU/SIL): {0:}/{1:}".format(len(ecu_ts), len(sil_ts)))

        # Loose the first 600ms
        sil_ts_sec = (sil_ts.index.values - sil_ts.index.values[0]) * 1.0e-6
        idx_sil = np.argmax(sil_ts[sil_ts_sec > 600.0e-3].index.values)
        idx_ecu = np.argmax(ecu_ts[ecu_ts.index.values >= sil_ts.index.values[idx_sil]].index.values)

        self._logger.debug("Startindices (ECU/SIL): {0:}/{1:}"
                           .format(idx_ecu, idx_sil))

        if len(ecu_ts) - idx_ecu - 1 != len(sil_ts) - idx_sil - 1:
            max_iloc = min(len(ecu_ts) - idx_ecu - 1, len(sil_ts) - idx_sil - 1)
            self._logger.debug("Last index is {0:}".format(max_iloc))
        else:
            max_iloc = -1

        ecu_df = ecu_ts.iloc[idx_ecu:max_iloc]
        sil_df = sil_ts.iloc[idx_sil:max_iloc]
        missing_ts = ecu_df - sil_df

        if True in pd.isnull(missing_ts).values:
            self._logger.warning("Some timestamps differ in SIL.")

            tmp = missing_ts[sil_df]
            mm = tmp[pd.isnull(tmp)]

            for idx in mm.index:
                # Index location
                loc = missing_ts.index.get_loc(idx)

                # Next value
                if len(missing_ts) > loc + 1:
                    val = missing_ts.iloc[loc + 1]

                    if pd.isnull(val):
                        # print("Twin NaN, due to earlier sim TS (allowed) since export is triggered within OOI cycle")
                        missing_ts.iloc[loc] = 0
                        missing_ts.iloc[loc + 1] = 0

                    else:
                        self._logger.debug("Missing timestamp: {}".format(val))

        # windowed = missing_ts[10:-10]
        nan_count = len(missing_ts[pd.isnull(missing_ts)])
        self._logger.debug("Total signal length/Missing values: {0:}/{1:}".format(len(missing_ts), nan_count))

        # noinspection PyBroadException
        try:
            for ts in missing_ts[pd.isnull(missing_ts)].index.values:
                idx = ecu_ts.index.get_loc(ts)

                self._logger.debug(idx)
                self._logger.debug(ecu_ts.index.values[idx-1:idx+2])
                ts_p = ecu_ts.index.values[idx]
                idx = sil_ts.index.get_loc(ts_p)
                self._logger.debug(idx)
                self._logger.debug(sil_ts.index.values[idx-1:idx+2])
        except Exception:
            self._logger.debug("Coder to dumb")

        # Now lift all NaN to make the signal plotable
        missing_ts[pd.isnull(missing_ts)] = 1

        # Histogram data
        ecu_ts_deltas = ecu_ts.values[1:] - ecu_ts.values[0:-1]
        sil_ts_deltas = sil_ts.values[1:] - sil_ts.values[0:-1]

        return {"NaN": nan_count,
                "Mean ECU": ecu_ts_deltas.mean(),
                "Standard Deviation ECU": ecu_ts_deltas.std(),
                "Mean SIL": sil_ts_deltas.mean(),
                "Standard Deviation SIL": sil_ts_deltas.std(),
                "Vec": missing_ts,
                "Number of samples in ECU": len(ecu_ts[idx_ecu:]),
                "Number of samples in SIL": len(sil_ts[idx_sil:]), }

    def _reindex(self, ref, target):
        """ Constructs a synchronized timestamp index. The ref timestamp is required to be later than the target
        timestamp. In case an index is missing in ref or target it is omited.
        :param ref: Timestamp data to sync to
        :param target: Original timestamp
        :return: a synchronized timestamp
        """
        # make a series containing itself
        ecu_series = pd.Series(ref, index=ref)
        sil_series = pd.Series(target, index=target)

        missing_ts = ecu_series - sil_series

        if True in pd.isnull(missing_ts).values:
            self._logger.warning("Some timestamps do not exists in SIL.")

            # Look in the subtraction of ecu and sil for the timestamps which belong to
            # sil and are NaN because there was no equal index in the ecu series
            mm = missing_ts[sil_series]

            # Work through the timestamps (worse case all) and try to find a nearest right neighbor
            for idx in mm.index:
                if pd.isnull(mm[idx]):
                    loc = missing_ts.index.get_loc(idx)

                    if len(missing_ts) > loc + 1:
                        # val = missing_ts.iloc[loc + 1]
                        val = missing_ts.index.values[loc + 1]

                        if val in ecu_series.index:
                            mm[idx] = val
                else:
                    mm[idx] = idx

            mm.iloc[-1] = sil_series.index.values[-1]
            return mm.values.astype(np.long)

        return target

    def execute(self, story):
        """ Build the timestamp delta signals,
            calculates mean and sigma,
            and the differences between ECU and SIL timestamps.
        """

        # indexes
        data = self._ecu_bsig_reader.get_signal_by_name(MTS_PACKAGE_TIME_STAMP)
        ecu_index = np.fromiter(data, np.long)
        ecu_ts_60 = pd.Series(ecu_index, ecu_index)

        data = self._sil_bsig_reader.get_signal_by_name(MTS_PACKAGE_TIME_STAMP)
        sil_index = np.fromiter(data, np.long)
        sil_ts_60 = pd.Series(sil_index, sil_index)

        self.results_60 = self.calc_nan_values(ecu_ts_60, sil_ts_60)

        test_step = ValTestStep(name="Missing Timestamps for DataProcCycle", res_type="Count",
                                unit=GblUnits.UNIT_L_NONE,
                                tag=self.testcase.get_spe_tag() + "-01", exp_res=self._config[EXP_RES])
        test_step.set_value(self.results_60["NaN"])
        self.testcase.add_test_step(test_step)
        if self.results_60["NaN"] > 0:
            assessment_state = ValAssessmentStates.FAILED
        else:
            assessment_state = ValAssessmentStates.PASSED
        test_step.add_assessment(self._mk_assessment(assessment_state))

        meas_file = self._data_manager.get_data_port("currentfile")
        head, tail = os.path.split(meas_file)
        story.add_heading("{0:}".format(tail), 2)
        # story.AddHeading("Timestamp availability", 1)
        # story.AddParagraph("This section gives detailed result about the " +
        #                    "SIL timestamp in comparison to the ECU timestamp.")

        text5 = "Missing timestamps in AlgoSenCycle (SIL)"

        # sig = self._to_signal("Missing Values DataProcCycle", GblUnits.UNIT_L_NONE, self.results_60["Vec"])
        # nan_plot, _ = sig.Plot([], out_path=outdir)
        # self._scale_drawing(nan_plot, 0.55)
        ecu_sig = AlgoSignal("ECU", ecu_ts_60, unit="us")

        reindexed = self._reindex(ecu_ts_60.index.values, sil_ts_60.index.values)
        missing = AlgoSignal("Missing", self.results_60["Vec"] * max(reindexed))
        sil_sig = AlgoSignal("SIL", sil_ts_60.values, reindexed, unit="us")
        nan_plot = self.plot_factory.histogram_plot(ecu_sig, sil_sig, [missing],
                                                    tolerance=[0, 62e3], title="Timestamps")

        story.AddImage(text5, os.path.join(self.out_directory, nan_plot))

        name = "Timestamp Delta properties"
        header = ["", "Mean", "Standard Deviation"]
        data = [["DataProcCyle (ECU)",
                 "{0:7.3f}".format(self.results_60["Mean ECU"]),
                 "{0:7.3f}".format(self.results_60["Standard Deviation ECU"])],
                ["DataProcCyle (SIL)",
                 "{0:7.3f}".format(self.results_60["Mean SIL"]),
                 "{0:7.3f}".format(self.results_60["Standard Deviation SIL"])]
                ]
        col_widths = [140, 150, 150]
        story.AddTable(name, data, header=header, colWidths=col_widths)

    @staticmethod
    def _scale_drawing(dwg, scale=0.5):
        """ Scales the drawing by the given factor.
            :param dwg: The drawing.
            :param scale: The scaling factor.
        """
        dwg.scale(scale, scale)
        dwg.height *= scale
        dwg.width *= scale

"""
CHANGE LOG:
-----------
$Log: tc_timestamps.py  $
Revision 1.1 2020/03/25 20:56:45CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/test_cases/project.pj
"""