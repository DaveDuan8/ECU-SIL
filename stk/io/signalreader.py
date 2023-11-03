"""
stk/io/signalreader
-------------------

Binary Signal Read Class

**User-API Interfaces**

  - `SignalReader` (signal file class)
  - `SignalReaderException`

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.18 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/02/13 08:28:06CET $
"""

__all__ = ['SignalReader', 'SignalReaderException']

# - import Python modules ----------------------------------------------------------------------------------------------
from numpy import inf, array
from os import path as opath, SEEK_END, SEEK_CUR
from struct import unpack
from zlib import decompress
from csv import Error, reader
from re import match, escape, IGNORECASE

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.error import StkError
from stk.util.helper import deprecation


# - defines ------------------------------------------------------------------------------------------------------------
SIG_NAME = 'SignalName'
SIG_TYPE = 'SignalType'
SIG_ARRAYLEN = 'ArrayLength'
SIG_OFFSET = 'Offsets'
SIG_SAMPLES = 'SampleCount'


# - classes ------------------------------------------------------------------------------------------------------------
class SignalReaderException(StkError):
    """general exception for SignalReader class"""
    def __init__(self, msg):
        """derived from std error"""
        delim = "=" * (len(msg) + 7) + "\n"
        StkError.__init__(self, "\n%sERROR: %s\n%s" % (delim, msg, delim))


class CsvReader(object):  # pylint: disable=R0924,R0902
    """
    **Delimited reader class**

    internal class used by SignalReader in case of reading csv type files

    use class `SignalReader` to read csv files
    """
    def __init__(self, filepath, **kwargs):
        """open / init cvs file
        """
        self._signal_names = []
        self._signal_values = {}
        self._signal_type = {}

        self._all_types = {long: 0, float: 1, str: 2}

        self._delimiter = kwargs.pop('delim', ';')
        if self._delimiter not in (';', ',', '\t', ' '):
            self._delimiter = ';'

        self._skip_lines = kwargs.pop('skip_lines', 0)
        self._skip_data_lines = kwargs.pop('skip_data_lines', 0)
        self._scan_type = kwargs.pop('scan_type', 'no_prefetch').lower()
        if self._scan_type not in ('prefetch', 'no_prefetch'):
            self._scan_type = 'prefetch'
        self._scan_opt = kwargs.pop('scan_opt', 'scan_auto').lower()
        if self._scan_opt not in ('scan_auto', 'scan_raw'):
            # self._scan_opt = self._match_type(self._scan_opt)
            if self._scan_opt == 'long':
                self._scan_opt = type(long(0))
            elif self._scan_opt == 'float':
                self._scan_opt = type(float(0.0))

        for opt in kwargs:
            deprecation('unused SignalReader option: ' + opt)

        self._selfopen = None

        if not hasattr(filepath, 'read'):
            self._fp = open(filepath, "r")
            self._selfopen = True
            self._file_path = filepath
        else:
            self._fp = filepath
            self._selfopen = False
            self._file_path = filepath.name

        # read file header
        try:
            self._csv = reader(self._fp, delimiter=self._delimiter)
            for _ in xrange(self._skip_lines):
                self._csv.next()

            # get all signals name
            self._signal_names = self._csv.next()

            if self._signal_names.count('') > 0:
                self._signal_names.remove('')
            for idx in xrange(len(self._signal_names)):
                self._signal_names[idx] = self._signal_names[idx].strip()
                self._signal_values[idx] = []

            if self._scan_type == 'prefetch':
                self._read_signals_values()
        except:
            self.close()
            raise

    def close(self):
        """close the file
        """
        if self._fp is not None:
            if self._selfopen:
                self._fp.close()
            self._fp = None

            self._signal_names = None
            self._signal_values = None

    def __len__(self):
        """Function returns the number of signals in the binary file.

        :return: The number of signals in the binary file.
        """
        return len(self._signal_names)

    def __str__(self):
        """returns file info"""
        return "<dlm: '%s', signals: %d>" % (self._fp.name, len(self))

    def siglen(self, _):
        """provides length of a signal, as csv's are of same length we do it the easy way

        :param: signal name (to be compatible to SignalReader method, not used here)
        :return: length of signal in file
        :rtype:  int
        """
        if len(self._signal_values[0]) == 0:
            self._read_signals_values(self._signal_names[0])
        return len(self._signal_values[0])

    @property
    def signal_names(self):
        """returns names of all signals

        :return: all signal names in file
        :rtype:  list
        """
        return self._signal_names

    def signal(self, signal, offset=0, count=0):
        """returns the values of a signal given as input.

        When signal_name doesn't exist it returns 'None'

        :param signal: the name of the signal
        :param offset: signal offset to start
        :param count: number of signal items to return
        :return: value of named signal or None
        """
        if type(signal) in (tuple, list):
            return [self.signal(s) for s in signal]

        self._read_signals_values(self._signal_names[signal] if type(signal) == int else signal)

        if type(signal) == str:
            signal = self._signal_names.index(signal)

        # todo: maybe we should convert already when reading...
        try:
            vals = array(self._signal_values[signal], dtype=[tt for tt, it in self._all_types.items()
                                                             if it == self._signal_type[signal]][0])
        except KeyError:
            vals = array(self._signal_values[signal], dtype=float)

        if offset + count == 0:
            return vals
        else:
            return vals[offset:offset + count]

    def _read_signals_values(self, signals_list=None):  # pylint: disable=R0912,R0915
        """
        Reads signal values from a simulation file - csv format.
        This function reads a list of signal given as input.
        When signals_list is 'None' all signal will be read

        :param signals_list:   the list of the signals
        :return: dictionary with extracted signals, empty {} in case of errors
        """
        if signals_list is None:
            signals_list = self._signal_names

        if type(signals_list) == str:
            signals_list = [signals_list]

        # prevent loading already loaded ones
        removes = [sig for sig in signals_list if len(self._signal_values[self._signal_names.index(sig)]) > 0]
        for rem in removes:
            signals_list.remove(rem)

        if len(signals_list) == 0:
            return

        for signal in signals_list:
            if signal not in self._signal_type:
                if self._scan_opt == 'scan_raw':
                    self._signal_type[self._signal_names.index(signal)] = 2
                else:
                    self._signal_type[self._signal_names.index(signal)] = 0

        self._fp.seek(0)
        # if skip_lines constructor parameter is not specified
        for _ in xrange(self._skip_lines + 1 + self._skip_data_lines):
            self._csv.next()

        if self._scan_opt == 'scan_raw':
            try:
                for row in self._csv:
                    for signal in signals_list:
                        try:
                            idx = self._signal_names.index(signal)
                            self._signal_values[idx].append(str(row[idx]))
                        except IndexError:
                            pass
                    # del row
            except Error as ex:
                raise SignalReaderException('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))

        elif self._scan_opt == 'scan_auto':
            try:
                for row in self._csv:
                    for signal in signals_list:
                        idx = self._signal_names.index(signal)
                        try:
                            if match(r"^(\d+)$", row[idx].lstrip()) is not None:
                                val = long(row[idx])
                            elif(match(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?\s*\Z",
                                       row[idx].lstrip()) is not None):
                                val = float(row[idx])
                            else:
                                val = str(row[idx])

                            if type(val) == str:
                                if match(r"[+]?1(\.)[#][Ii][Nn]", val.lstrip()) is not None:
                                    val = inf
                                elif match(r"-1(\.)[#][Ii][Nn]", val.lstrip()) is not None:
                                    val = -inf
                            self._signal_values[idx].append(val)
                            self._signal_type[idx] = max(self._all_types[type(val)], self._signal_type[idx])
                        except:
                            self._signal_type[idx] = type(float)
                    # del row
            except Error as ex:
                raise SignalReaderException('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))
        else:
            try:
                for row in self._csv:
                    for signal in signals_list:
                        idx = self._signal_names.index(signal)
                        self._signal_values[idx].append(self._scan_opt(row[idx]))
            except Error as ex:
                raise SignalReaderException('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))


class BsigReader(object):  # pylint: disable=R0902,R0924
    """bsig reader class

    internal class used by SignalReader to read binary signal files (type bsig2 and bsig3)

    use class `SignalReader` to read files
    """
    def __init__(self, fp, **kw):  # pylint: disable=R0912,R0915
        """set default values

        :param fp: file to use, can be a file pointer to an already open file or a name of file
        :keyword use_numpy: use numpy for signal values, default: True
        """
        self._arr_frmt = {0x0008: 'B', 0x8008: 'b', 0x0010: 'H', 0x8010: 'h', 0x0020: 'L', 0x8020: 'l', 0x0040: 'Q',
                          0x8040: 'q', 0x9010: 'f', 0x9020: 'd'}
        self._sig_frmt = {'c': 1, 'b': 1, 'B': 1, 'h': 2, 'H': 2, 'I': 4, 'l': 4, 'L': 4, 'q': 8, 'Q': 8,
                          'f': 4, 'd': 8}
        file_header = 24

        self._fp = fp
        self._npusage = kw.pop('use_numpy', True)
        self._name_sense = kw.pop('sensitive', True)
        self._selfopen = None

        try:
            if hasattr(self._fp, 'read'):
                self._fp.seek(0)
                self._selfopen = False
            else:
                # noinspection PyTypeChecker
                self._fp = open(self._fp, "rb")
                self._selfopen = True

            # read global header
            if self._read_sig('c' * 4) != ('B', 'S', 'I', 'G'):
                raise SignalReaderException("given file is not of type BSIG!")
            version = self._read_sig('B' * 3)
            if version[0] not in (2, 3):  # we support version 2 and 3 by now
                raise SignalReaderException("unsupported version: %d.%d.%d, supporting only V2 & V3!" % version)
            self._version = version[0]
            self._signal_data = []
            self._offstype = 'I' if self._version == 2 else 'Q'

            # get total size of file
            self._fp.seek(0, SEEK_END)
            self._file_size = self._fp.tell()
            self._fp.seek(-file_header, SEEK_CUR)

            # read file header
            signal_count, self._block_size, self._hdr_size, offset_size = self._read_sig('IIII')
            self._read_sig('B' * 3)  # internal version is unused, read over
            self._compression = self._read_sig('B')[0] == 1
            if self._read_sig('c' * 4) != ('B', 'I', 'N', '\x00'):  # bin signature
                raise SignalReaderException("BSIG signature wrong!")

            # read signal description
            self._fp.seek(self._file_size - file_header - self._hdr_size)  # = self._hdr_offset
            for _ in xrange(signal_count):
                sig_name_len = self._read_sig('H')[0]
                signal_name = "".join(self._read_sig('c' * sig_name_len))
                array_len, stype = self._read_sig('II')
                self._signal_data.append({SIG_NAME: signal_name, SIG_TYPE: stype, SIG_ARRAYLEN: array_len})

            # read offsets data
            self._fp.seek(self._file_size - file_header - self._hdr_size - offset_size)
            for sig in self._signal_data:
                offset_count, sig[SIG_SAMPLES] = self._read_sig('II')
                sig[SIG_OFFSET] = self._read_sig(self._offstype * offset_count) if offset_count else []
        except SignalReaderException:
            self.close()
            raise
        except:
            self.close()
            raise SignalReaderException("Error while reading signal information, corruption of data?")

    def close(self):
        """close signal file
        """
        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None

                self._signal_data = None
            except:
                raise SignalReaderException("An error occurred while closing the file.")

    def __len__(self):
        """Function returns the number of signals in the binary file.

        :return: number of signals in the binary file.
        """
        return len(self._signal_data)

    def __str__(self):
        """returns file info"""
        return "<bsig%d: '%s', signals: %d>" % (self._version, self._fp.name, len(self))

    def siglen(self, signal):
        """provides length of a signal, as csv's are of same length we do it the easy way

        :param signal: name of signal
        :return: length of signal
        :rtype:  int
        """
        if signal is None:
            return self._signal_data[0][SIG_SAMPLES]

        if self._name_sense:
            sigdet = next((s for s in self._signal_data if s[SIG_NAME] == signal), None)
        else:
            sigdet = next((s for s in self._signal_data if s[SIG_NAME].lower() == signal.lower()), None)
        if sigdet is None:
            raise SignalReaderException("no signal by that name found: %s" % str(signal))

        return sigdet[SIG_SAMPLES]

    def signal(self, signal, offset=None, count=None):  # pylint: disable=R0912
        """Function returns the data for the signal with the specified index.

        :param signal: index / name of signal or list of the signals
        :param offset: data offset of signal
        :param count: length of data
        :return: signal data as an array (default) or list as defined during reader initialisation
        :rtype: array or list
        """
        # check for input argument validity
        if type(signal) in (tuple, list):
            return [self.signal(s) for s in signal]
        elif type(signal) == int and 0 <= signal < len(self._signal_data):
            sigdet = self._signal_data[signal]
        else:
            if self._name_sense:
                sigdet = next((s for s in self._signal_data if s[SIG_NAME] == signal), None)
            else:
                sigdet = next((s for s in self._signal_data if s[SIG_NAME].lower() == signal.lower()), None)
            if sigdet is None:
                raise SignalReaderException("signal not found: %s" % signal)

        # align offset and count, count is initially the length, but we use it as stop point and offset as start point
        if offset is None:
            offset = 0
        elif offset < 0:
            offset = sigdet[SIG_SAMPLES] + offset
        if count is None:
            count = sigdet[SIG_SAMPLES]
        elif count < 0 or offset + count > sigdet[SIG_SAMPLES]:
            raise SignalReaderException("offset / count for signal %s is out of range: %s / %s" %
                                        (signal, str(offset), str(count)))
        else:
            count += offset

        frmt = self._arr_frmt[sigdet[SIG_TYPE]]  # data format
        dlen = self._sig_frmt[frmt]  # length of one data point
        blkl = self._block_size / dlen  # real block length
        alen = sigdet[SIG_ARRAYLEN]  # array length of signal
        sig = []  # extracted signal

        # increment with array length
        offset *= alen
        count *= alen

        # precalc reduced offsets
        sigoffs = list(sigdet[SIG_OFFSET])
        while count < (len(sigoffs) - 1) * blkl:  # cut last offsets
            sigoffs.pop(len(sigoffs) - 1)

        while offset >= blkl:  # cut first offsets
            sigoffs.pop(0)
            offset -= blkl  # reduce starting point
            count -= blkl  # reduce stop point

        # without compression we could even cut down more reading,
        # but I'll leave it for now as it makes more if then else

        # read data blocks
        for offs in sigoffs:
            self._fp.seek(offs)
            if self._compression:
                data = self._fp.read(self._read_sig('I')[0])
                data = decompress(data)
            else:
                data = self._fp.read(self._block_size)

            data = unpack(frmt * (len(data) / dlen), data)
            sig.extend(data)

        if self._npusage:
            if alen == 0:
                return array(sig[offset:count], dtype=frmt)
            elif alen == 1:
                return array(sig[offset:count], dtype=frmt)
            return array(sig[offset:count], dtype=frmt).reshape(((count - offset) / alen, alen))
        else:
            if alen == 1:
                return sig[offset:count]
            return [sig[i:i + alen] for i in xrange(offset, count, alen)]

    @property
    def signal_names(self):
        """returns names of all signals with the specified index.

        :return: all signal names in file
        :rtype:  list
        """
        return [sig[SIG_NAME] for sig in self._signal_data]

    def _read_sig(self, stype):
        """read signal of given type
        """
        try:
            return unpack(stype, self._fp.read(self._sig_frmt[stype[0]] * len(stype)))
        except:
            raise SignalReaderException("An error occured while reading binary data.")


class SignalReader(object):
    """
    **MAIN Class for Signal File Read.** (\\*.bsig (aka \\*.bin), \\*.csv)

    open, step through, read signals and close a signal file, provide list of signal names

    by default the **values are returned as numpy array**, see `__init__` how to configure for python lists

    for csv files several options (like delimiter) are supported, see `__init__` for more details

    even if the usage looks like calling a dict *a SignalReader instance is no dict:*

    - when getting a signal using ``sr['my_signal_name']`` just that signal is read from the file;
    - adding or deleting signals is not possible, it's just a reader;
    - there are no dict functions like d.keys(), d.values(), d.get() etc.

    supported functions (see also Examples below):

    -with              open and integrated close for a signal file
    -get               values of signal with name or index: ``sr['my_name'], sr[2]``
    -len               number of signals: ``len(sr)``
    -in                check if signal with name is available: ``if 'my_sig' in sr:``
    -for               loop over all signals with name and values: ``for n, v in sr:``
    -signal_names      list of all signal names (like dict.keys()): ``sr.signal_names``,
                       also supports wildcard for name (see EXAMPLE 3:)

    usage (example)
    ---------------

    .. python::
        # read csv files:
        reader = SignalReader(<file.csv>,
                              'delim'=<delimiter>,
                              'scan_type'=<'prefetch','no_prefetch'>,
                              'scan_opt'=<'scan_auto','scan_raw','float',...>,
                              'skip_lines'=<number_of_header_lines_to_skip>,
                              'skip_data_lines'=<number_of_data_lines_to_skip>)
        # read bsig files (version 2 or 3)
        reader = SignalReader(<file.bsig>)

        # check if signal with name is stored in file:
        if "MTS.Package.TimeStamp" not in reader:
            print("TimeStamp missing in signal file")

    Examples:

    .. python::
        import numpy as np
        from stk.io.signalreader import SignalReader, SignalReaderException

        # EXAMPLE 1
        sr = SignalReader('file_hla_xyz.txt', delim ='\t', scan_type='NO_PREFETCH')
        # get values
        read_values = sr['lux_R2G']
        sr.close()

        # EXAMPLE 2
        sr = SignalReader('file_sla_xyz.csv',delim =',',skip_lines=8)
        # read only signal 'timestamp'
        values = sr['timestamp'] # gets the timestamp signal
        values = sr[0] # gets the signal by index 0
        sr.close()

        # EXAMPLE 3
        with SignalReader('file_hla_xyz.bsig') as sr:
            signals = sr[['Time stamp','Cycle counter']] # retrieves a list of both signals --> [[<sig1>], [<sig2>]]
            signals = sr[['sig_obj_dist*']]  # matching: sig_obj_dist_x, sig_obj_dist_y, sig_obj_distrel_x, ...

        # EXAMPLE 4
        with SignalReader('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

        # EXAMPLE 5
        with SignalReader('file_fct.bsig') as sr:
            for n, v in sr:  # iterate over names and signals
                print("%s: %d" % (n, v.size))

        with SignalReader('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

        # EXAMPLE 6
        instance_ARS = SignalReader('file_ars_xyz.csv', delim =';',scan_opt = 'float')
        ...
        instance_ARS.close()


        import numpy as np
        from stk.io.signalreader import SignalReader, SignalReaderException

        # EXAMPLE 1
        sr = SignalReader('file_hla_xyz.txt', delim ='\t', scan_type='NO_PREFETCH')
        # get values
        read_values = sr['lux_R2G']
        sr.close()

        # EXAMPLE 2
        sr = SignalReader('file_sla_xyz.csv',delim =',',skip_lines=8)
        # read only signal 'timestamp'
        values = sr['timestamp'] # gets the timestamp signal
        values = sr[0] # gets the signal by index 0
        sr.close()

        # EXAMPLE 3
        with SignalReader('file_hla_xyz.bsig') as sr:
            signals = sr[['Time stamp','Cycle counter']] # retrieves a list of both signals --> [[<sig1>], [<sig2>]]
            signals = sr[['sig_obj_dist*']]  # matching: sig_obj_dist_x, sig_obj_dist_y, sig_obj_distrel_x, ...

        # EXAMPLE 4
        with SignalReader('file_hla_xyz.bsig') as sr:
            signals = sr['Time stamp':50:250] # retrieves 200 samples of time stamp signal from offset 50 onwards

        # EXAMPLE 5
        instance_ARS = SignalReader('file_ars_xyz.csv', delim =';',scan_opt = 'float')
        ...
        instance_ARS.close()

    For reading blocks of signals together or object signals (the signals with [%] in the name)
    the extended class `SignalLoader` can be used.

    To extract single objects from the object signals (e.g. Object of Interest, OOI)
    there is a further extension in stk:
    `stk.obj.obj_converter.py` can be configured to extract objects with a given min. life time
    from defined signals.
    """

    def __init__(self, filename, **kw):
        """open the binary file by its name, supported formats: bsig 2, 3, csv

        :param filename: path/to/file.name

        :keyword type: type of file can be set explicitly, set to 'bsig' will force it to be a bsig,
                       by default extensions 'bsig', 'bin' and 'tstp' will be recognised as bsig files.
        :keyword use_numpy: (bsig files) boolean value that indicates whether using numpy arrays for signal values,
                            default: True
        :keyword sensitive: (bsig files)boolean value that indicates whether to treat signal names case sensitive,
                            default: True
        :keyword delim: (csv files) delimiter char for columns
        :keyword scan_type: (csv files) can be 'no_prefetch' or 'prefetch' to read in data at init
        :keyword scan_opt: (csv files) 'can be 'scan_auto', 'scan_raw' or e.g. 'float', 'long' or 'str'
        :keyword scip_lines: (csv files) how many lines should be scripped / ignored reading in at start of file
        :keyword scip_data_lines: (csv files) how many lines of data should be scripped reading in at start
        """
        self._fp = filename
        self._name_sense = True

        if opath.splitext(self._fp.name if hasattr(self._fp, 'read')
                          else filename)[1].lower() in ('.bsig', '.bin', '.tstp') or kw.pop('type', None) == 'bsig':
            self._name_sense = kw.get('sensitive', True)
            self._reader = BsigReader(self._fp, **kw)
            self._type = "bsig"
        else:
            self._reader = CsvReader(self._fp, **kw)
            self._type = "dlm"

        self._signal_names = self._reader.signal_names
        self._iter_idx = 0

    def __enter__(self):
        """being able to use with statement"""
        return self

    def __exit__(self, *_):
        """close down file"""
        self.close()

    def close(self):
        """close file"""
        self._reader.close()

    def __str__(self):
        """returns the type and number of signals"""
        return str(self._reader)

    def __len__(self):
        """return number of signals from reader"""
        return len(self._reader)

    def signal_length(self, signal=None):
        """length of a signal

        :param signal: name of signal length should be returned
        :return: signal length
        :rtype: int
        """
        return self._reader.siglen(signal)

    def __iter__(self):
        """start iterating through signals"""
        self._iter_idx = 0
        return self

    def next(self):
        """next signal item to catch and return"""
        if self._iter_idx >= len(self._signal_names):
            raise StopIteration
        else:
            self._iter_idx += 1
            return self._signal_names[self._iter_idx - 1], self[self._iter_idx - 1]

    def __contains__(self, name):
        """checks if signal name is stored in SignalReader

        :param name: signal name to check
        :return: bool
        """
        return name in self._signal_names

    def __getitem__(self, signal):
        """provide signal by name or index,

        if index is a slice use start as index,
        stop as offset and step as count

        :param signal: signal name or index or sliced index, a signal name can be extended with '*' as wildcard
        :type  signal: str, int, tuple/list,
        :return:  signal with type as defined in reader initiation
        :rtype:   array or list
        """
        # [Offset:Offset + SampleCount]
        try:
            if type(signal) in (int, str):
                return self._reader.signal(signal)
            elif type(signal) in (tuple, list):
                signal = self._signal_expand(signal)
                if set(signal).issubset(self._signal_names):
                    return self._reader.signal(signal)
                else:
                    return self._reader.signal(signal[0], signal[1], signal[2])
            elif type(signal) == slice:  # not nice, but no other strange construct needed
                return self._reader.signal(signal.start, signal.stop, signal.step)
            else:
                raise IndexError
        except (IndexError, SignalReaderException):
            raise
        except:
            raise SignalReaderException("Data corruption inside signal file, unable to read signal '{}'!"
                                        .format(signal))

    def _signal_expand(self, signals):
        """expand signals when asterix wildcard is in use
        """
        sigs = []
        for i in signals:
            if '*' in i:
                k = '^' + escape(i).replace('\\*', '.*') + '$'
                for l in self.signal_names:
                    if match(k, l, IGNORECASE if self._name_sense else 0):
                        sigs.append(l)
            else:
                sigs.append(i)

        return sigs

    @property
    def signal_names(self):
        """list of all signal names

        :return: all signal names in file
        :rtype:  list
        """
        return self._signal_names


"""
CHANGE LOG:
-----------
$Log: signalreader.py  $
Revision 1.18 2017/02/13 08:28:06CET Mertens, Sven (uidv7805) 
asterisk -> asterix
Revision 1.17 2016/11/29 12:04:45CET Hospes, Gerd-Joachim (uidv8815)
update docu
Revision 1.16 2016/10/27 11:24:54CEST Hospes, Gerd-Joachim (uidv8815)
finetuning and further docu
Revision 1.15 2016/10/25 12:20:09CEST Hospes, Gerd-Joachim (uidv8815)
add ObjSignals class with tests and docu
Revision 1.14 2016/09/19 12:11:13CEST Hospes, Gerd-Joachim (uidv8815)
wildcard for signal list
Revision 1.13 2016/07/11 16:42:55CEST Mertens, Sven (uidv7805)
fix for zero length signals
Revision 1.12 2016/03/04 18:11:48CET Hospes, Gerd-Joachim (uidv8815)
let SignalReaderExceptions pass as they are
Revision 1.11 2015/10/22 11:04:43CEST Hospes, Gerd-Joachim (uidv8815)
provide length of signals without loading the signal, add exception if signal can not be extracted
--- Added comments ---  uidv8815 [Oct 22, 2015 11:04:44 AM CEST]
Change Package : 389210:1 http://mks-psad:7002/im/viewissue?selection=389210
Revision 1.10 2015/10/16 16:55:22CEST Hospes, Gerd-Joachim (uidv8815)
docu extension
--- Added comments ---  uidv8815 [Oct 16, 2015 4:55:23 PM CEST]
Change Package : 387188:1 http://mks-psad:7002/im/viewissue?selection=387188
Revision 1.9 2015/10/16 13:46:59CEST Hospes, Gerd-Joachim (uidv8815)
add 'in' to SignalReader
Revision 1.8 2015/09/28 12:18:32CEST Mertens, Sven (uidv7805)
close file when corrupt
--- Added comments ---  uidv7805 [Sep 28, 2015 12:18:32 PM CEST]
Change Package : 380877:1 http://mks-psad:7002/im/viewissue?selection=380877
Revision 1.7 2015/07/14 09:40:52CEST Mertens, Sven (uidv7805)
fix for 0 length signals
--- Added comments ---  uidv7805 [Jul 14, 2015 9:40:52 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.6 2015/07/02 12:10:48CEST Mertens, Sven (uidv7805)
fix for empty signals
--- Added comments ---  uidv7805 [Jul 2, 2015 12:10:49 PM CEST]
Change Package : 350659:4 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.5 2015/06/30 11:10:37CEST Mertens, Sven (uidv7805)
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:10:38 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.4 2015/06/24 16:35:55CEST Mertens, Sven (uidv7805)
removing not
--- Added comments ---  uidv7805 [Jun 24, 2015 4:35:55 PM CEST]
Change Package : 350659:1 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.3 2015/06/17 14:07:56CEST Mertens, Sven (uidv7805)
minor fix for multi array signals
--- Added comments ---  uidv7805 [Jun 17, 2015 2:07:56 PM CEST]
Change Package : 338364:1 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.2 2015/06/02 09:53:53CEST Mertens, Sven (uidv7805)
adding case insensitive support for signal names
--- Added comments ---  uidv7805 [Jun 2, 2015 9:53:53 AM CEST]
Change Package : 338364:1 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.1 2015/04/23 19:04:31CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
Revision 1.22 2015/04/16 10:59:19CEST Hospes, Gerd-Joachim (uidv8815)
enhance signal_names usage
--- Added comments ---  uidv8815 [Apr 16, 2015 10:59:20 AM CEST]
Change Package : 328888:1 http://mks-psad:7002/im/viewissue?selection=328888
Revision 1.21 2015/04/10 13:49:56CEST Mertens, Sven (uidv7805)
removing V1 support which is also not supported by BinViewer a few years now
--- Added comments ---  uidv7805 [Apr 10, 2015 1:49:56 PM CEST]
Change Package : 318014:3 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.20 2015/04/09 13:30:32CEST Mertens, Sven (uidv7805)
remove unneccessary file reads
Revision 1.19 2015/04/08 15:01:49CEST Mertens, Sven (uidv7805)
trial and error
--- Added comments ---  uidv7805 [Apr 8, 2015 3:01:49 PM CEST]
Change Package : 318014:1 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.18 2015/04/08 14:10:28CEST Mertens, Sven (uidv7805)
escape properly
--- Added comments ---  uidv7805 [Apr 8, 2015 2:10:28 PM CEST]
Change Package : 318014:1 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.17 2015/04/08 11:50:09CEST Mertens, Sven (uidv7805)
removing some branches to speed up
--- Added comments ---  uidv7805 [Apr 8, 2015 11:50:09 AM CEST]
Change Package : 318014:1 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.16 2015/04/08 10:11:22CEST Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Apr 8, 2015 10:11:23 AM CEST]
Change Package : 318014:1 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.15 2015/04/07 16:54:54CEST Mertens, Sven (uidv7805)
- new option for bsig: use_numpy,
- rewrite without using ctypes,
- trying to support bsig 1 format again.
Revision 1.13 2015/02/26 16:08:20CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Feb 26, 2015 4:08:20 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.12 2015/02/10 08:22:53CET Mertens, Sven (uidv7805)
- internal name alignment,
- docu fix,
- bug fix for signal read in
Revision 1.11 2015/01/30 08:29:03CET Mertens, Sven (uidv7805)
fix for wrong float format
Revision 1.10 2015/01/22 11:05:02CET Mertens, Sven (uidv7805)
adaptation to wrong indexing if negative
--- Added comments ---  uidv7805 [Jan 22, 2015 11:05:03 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.9 2015/01/13 15:08:31CET Mertens, Sven (uidv7805)
- one less loop for array read out,
- pylint fixes
Revision 1.8 2014/12/17 17:13:37CET Hospes, Gerd-Joachim (uidv8815)
fix kw type
--- Added comments ---  uidv8815 [Dec 17, 2014 5:13:38 PM CET]
Change Package : 283688:1 http://mks-psad:7002/im/viewissue?selection=283688
Revision 1.7 2014/12/17 13:36:42CET Mertens, Sven (uidv7805)
minor internal name fixes
--- Added comments ---  uidv7805 [Dec 17, 2014 1:36:42 PM CET]
Change Package : 292403:1 http://mks-psad:7002/im/viewissue?selection=292403
Revision 1.6 2014/09/30 15:37:28CEST Mertens, Sven (uidv7805)
tiny clearance
--- Added comments ---  uidv7805 [Sep 30, 2014 3:37:28 PM CEST]
Change Package : 267399:1 http://mks-psad:7002/im/viewissue?selection=267399
Revision 1.5 2014/09/30 13:06:49CEST Mertens, Sven (uidv7805)
minor adaptation to length and first signal as binviewer reports same
--- Added comments ---  uidv7805 [Sep 30, 2014 1:06:50 PM CEST]
Change Package : 267399:1 http://mks-psad:7002/im/viewissue?selection=267399
Revision 1.4 2014/09/30 12:50:43CEST Mertens, Sven (uidv7805)
str repr adaptation
--- Added comments ---  uidv7805 [Sep 30, 2014 12:50:44 PM CEST]
Change Package : 267399:1 http://mks-psad:7002/im/viewissue?selection=267399
Revision 1.3 2014/09/30 12:43:59CEST Mertens, Sven (uidv7805)
bsig3 support and some adaptations
--- Added comments ---  uidv7805 [Sep 30, 2014 12:43:59 PM CEST]
Change Package : 267399:1 http://mks-psad:7002/im/viewissue?selection=267399
Revision 1.2 2014/09/09 09:58:22CEST Mertens, Sven (uidv7805)
update for missing test data
--- Added comments ---  uidv7805 [Sep 9, 2014 9:58:22 AM CEST]
Change Package : 260446:1 http://mks-psad:7002/im/viewissue?selection=260446
Revision 1.1 2014/09/09 09:23:38CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/io/project.pj
"""
