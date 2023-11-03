"""
signal.py
---------

signal processor to read and write bsig's and csv's
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from csv import Dialect, QUOTE_NONNUMERIC, register_dialect

# - import HPC modules -------------------------------------------------------------------------------------------------
from .signalreader import SignalReader
from .signalwriter import SignalWriter


# - classes / functions ------------------------------------------------------------------------------------------------
class SignalException(Exception):
    """general exception for SignalReader class"""

    def __init__(self, msg):
        """derive from std error"""
        Exception.__init__(self, "ERROR: {}".format(msg))


class MetaData(Dialect):  # pylint: disable=R0903
    """Describe the usual properties of Excel-generated CSV files."""

    delimiter = ';'
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_NONNUMERIC


register_dialect("conti-excel", MetaData)


class Signal(object):  # pylint: disable=R0903
    r"""
    **Signal File Read and Write** (\*.bsig (aka \*.bin), \*.csv)

    open, step through, read or write signals and close a signal file, provide list of signal names

    by default the **values read are returned as numpy array**, see `__init__` how to configure for python lists

    for csv files several options (like delimiter) are supported, see `__init__` for more details

    even if the usage looks like calling a dict *a Signal instance is no dict:*

    - when getting a signal using ``sr['my_signal_name']`` just that signal is read from the file;
    - adding or deleting signals is not possible, it's just a reader;
    - there are no dict functions like d.keys(), d.values(), d.get() etc.

    supported functions (see also Examples below):

        - with              open and integrated close for a signal file
        - get               values of signal with name or index: ``sr['my_name'], sr[2]``
        - len               number of signals: ``len(sr)``
        - in                check if signal with name is available: ``if 'my_sig' in sr:``
        - for               loop over all signals with name and values: ``for n, v in sr:``
        - signal_names      list of all signal names (like dict.keys()): ``sr.signal_names``

    for the writing use mode='w' and use type='csv' or type='bsig'
    if later is used you might want to step back using V2 format: v2format=True

    Example 1::

        # read csv files:
        reader = Signal(<file.csv>,
                        'delim'=<delimiter>,
                        'scan_type'=<'prefetch','no_prefetch'>,
                        'scan_opt'=<'scan_auto','scan_raw','float',...>,
                        'skip_lines'=<number_of_header_lines_to_skip>,
                        'skip_data_lines'=<number_of_data_lines_to_skip>)

        # read bsig files (version 2 or 3)
        reader = Signal(<file.bsig>)

        # check if signal with name is stored in file:
        if "MTS.Package.TimeStamp" not in reader:
            print("TimeStamp missing in signal file")

    Example 2::

        import numpy as np
        from hpc import Signal, SignalException

        sr = Signal('file_hla_xyz.txt', delim ='\t', scan_type='NO_PREFETCH')
        # get values
        read_values = sr['lux_R2G']
        sr.close()

    Example 3::

        sr = Signal('file_sla_xyz.csv',delim =',',skip_lines=8)
        # read only signal 'timestamp'
        values = sr['timestamp'] # gets the timestamp signal
        values = sr[0] # gets the signal by index 0
        sr.close()

    Example 4::

        with Signal('file_hla_xyz.bsig') as sr:
            signals = sr[['Time stamp','Cycle counter']] # retrieves a list of both signals --> [[<sig1>], [<sig2>]]

    Example 5::

        with Signal('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

    Example 6::

        with Signal('file_fct.bsig') as sr:
            for n, v in sr:  # iterate over names and signals
                print("{}: {}".format(n, v.size))

        with Signal('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

    Example 7::

        instance_ARS = Signal('file_ars_xyz.csv', delim =';',scan_opt = 'float')
        ...
        instance_ARS.close()


        import numpy as np
        from hpc import Signal, SignalException

    Example 8::

        sr = Signal('file_hla_xyz.txt', delim ='\t', scan_type='NO_PREFETCH')
        # get values
        read_values = sr['lux_R2G']
        sr.close()

    Example 9::

        sr = Signal('file_sla_xyz.csv',delim =',',skip_lines=8)
        # read only signal 'timestamp'
        values = sr['timestamp'] # gets the timestamp signal
        values = sr[0] # gets the signal by index 0
        sr.close()

    Example 10::

        with Signal('file_hla_xyz.bsig') as sr:
            signals = sr[['Time stamp','Cycle counter']] # retrieves a list of both signals --> [[<sig1>], [<sig2>]]

    Example 11::

        with Signal('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

    Example 12::

        instance_ARS = Signal('file_ars_xyz.csv', delim =';',scan_opt = 'float')
        ...
        instance_ARS.close()

    Example 13::

        # just write some

        with Signal('file_hla_xyz.bsig', mode='w') as sw:
            sw.append('Time stamp', np.array([0, 1, 2, 3, 4, 5, 6, 7]))
            sw.append('Cycle counter', np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))

    Example 14::

        # reorganize

        bsig_in_file, bsig_out_file = 'Snapshot_201x.x.y_at_h.m.s_FCT.bsig', 'Snapshot_201x.x.y_at_h.m.s_all.bsig'
        sig_list = ['MTS.Timestamp', 'MTS.Cyclecounter', 'SIM VFB.FCTVehicle.HEAD.Header.uiStructSize', ...]

        with Signal(bsig_in_file) as sin, Signal(bsig_out_file, mode='w') as sout:
            for sig in sig_list:
                sout.append(sig, sin[sig])

    Example 15::

        # CSV

        with Signal('Snapshot_xyz.csv', mode='w') as sw:
            sw.append('signal 1', np.array([0, 1, 2, 3, 4, 5, 6, .....]))
            ...

    """

    def __new__(cls, *args, **kwargs):
        """overload to encapsulate either reader or writer"""
        kw = dict(kwargs)
        mode = kw.pop('mode', 'r')
        kw["exc"] = SignalException
        if mode == 'r':
            return SignalReader(*args, **kw)
        if mode == 'w':
            return SignalWriter(*args, **kw)

        raise SignalException("mode '{}' is not supported, use 'r' or 'w'!".format(mode))

    __enter__ = __exit__ = None
