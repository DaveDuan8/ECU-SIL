"""
signalreader.py
---------------

signal reader class
"""
from __future__ import division

__all__ = ['SignalReader']

# - import Python modules ----------------------------------------------------------------------------------------------
from os import SEEK_END, SEEK_CUR
from os.path import splitext
from struct import unpack
from zlib import decompress
from csv import Error, reader
from re import match
from numpy import inf, array, int64
from six import PY2, PY3

if PY2:
    range = xrange  # pylint: disable=W0622,C0103,E0602

# - import HPC modules -------------------------------------------------------------------------------------------------
from . import BSIG_HDR, BSIG_FTR, StringTypes, SIG_NAME, SIG_TYPE, SIG_ARRAYLEN, SIG_OFFSET, SIG_SAMPLES


# - classes ------------------------------------------------------------------------------------------------------------
class CsvReader(object):  # pylint: disable=R0902
    """
    **Delimited reader class**

    internal class used by SignalReader in case of reading csv type files

    use class `SignalReader` to read csv files
    """

    def __init__(self, filepath, **kwargs):  # pragma: no cover # pylint: disable=R0912,R1260
        """open / init cvs file"""
        self._signal_names = []
        self._signal_values = {}
        self._signal_type = {}
        self._all_types = {int64: 0, float: 1, str: 2}

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
            if self._scan_opt in ('int', 'long',):
                self._scan_opt = int64
            elif self._scan_opt == 'float':
                self._scan_opt = float

        self._exc = kwargs.pop("exc")
        self._fp, self._selfopen = None, False

        if hasattr(filepath, 'read'):
            self._fp = filepath
            self._file_path = getattr(filepath, "name", str(filepath))
            # self._csv = reader(self._fp, delimiter=self._delimiter, **kwargs)
        elif isinstance(filepath, StringTypes):
            self._file_path = filepath
            self._fp = open(filepath, "r")
            self._selfopen = True
            # self._csv = reader(self._fp, delimiter=self._delimiter, **kwargs)
        # else:
        #     self._fp = filepath
        #     self._fp = [i.split(self._delimiter) for i in self._fp]
        #     self._csv = iter(self._fp)

        # read file header
        try:
            self._csv = reader(self._fp, delimiter=self._delimiter, **kwargs)

            for _ in range(self._skip_lines):
                if PY2:
                    self._csv.next()
                else:
                    next(self._csv)

            # get all signals name
            if PY2:
                self._signal_names = self._csv.next()
            else:
                self._signal_names = next(self._csv)

            for _ in range(self._skip_data_lines):
                if PY2:
                    self._csv.next()
                else:
                    next(self._csv)

            if self._signal_names.count('') > 0:
                self._signal_names.remove('')
            self._signal_values = {i: [] for i in range(len(self._signal_names))}

            if self._scan_type == 'prefetch':
                self._read_signals_values()
        except Exception:
            self.close()
            raise

    def close(self):  # pragma: no cover
        """close the file"""
        if self._fp is not None:
            if self._selfopen:
                self._fp.close()
            self._fp = None

            self._signal_names = None
            self._signal_values = None

    def __len__(self):  # pragma: no cover
        """
        return the number of signals in the binary file.

        :return: The number of signals in the binary file.
        :rtype: int
        """
        return len(self._signal_names)

    def __str__(self):  # pragma: no cover
        """:return str: file info"""
        return "<dlm: '%s', signals: %d>" % (self._fp.name, len(self))

    def siglen(self, _):  # pragma: no cover
        """
        provide length of a signal, as csv's are of same length we do it the easy way

        :param: signal name (to be compatible to SignalReader method, not used here)
        :return: length of signal in file
        :rtype: int
        """
        if len(self._signal_values[0]) == 0:
            self._read_signals_values(self._signal_names[0])
        return len(self._signal_values[0])

    @property
    def signal_names(self):  # pragma: no cover
        """
        return names of all signals

        :return: all signal names in file
        :rtype: list
        """
        return self._signal_names

    def signal(self, signal, offset=0, count=0):  # pragma: no cover
        """
        return the values of a signal given as input.

        When signal_name doesn't exist it returns 'None'

        :param str signal: the name of the signal
        :param int offset: signal offset to start
        :param count count: number of signal items to return
        :return: value of named signal or None
        :rtype: numpy.array
        """
        if isinstance(signal, (tuple, list,)):
            return [self.signal(s) for s in signal]

        self._read_signals_values(self._signal_names[signal] if isinstance(signal, int) else signal)

        if isinstance(signal, StringTypes):
            idx = self._signal_names.index(signal)
        else:
            idx = signal

        try:
            vals = array(self._signal_values[idx], dtype=[tt for tt, it in list(self._all_types.items())
                                                          if it == self._signal_type[idx]][0])
        except KeyError:
            vals = array(self._signal_values[idx], dtype=float)

        if offset + count == 0:
            return vals
        return vals[offset:offset + count]

    def _read_signals_values(self, signals_list=None):  # pragma: no cover # pylint: disable=R0912,R0915,R1260
        """
        Read signal values from a simulation file - csv format.
        This function reads a list of signal given as input.
        When signals_list is 'None' all signal will be read

        :param list signals_list:   the list of the signals
        """
        if signals_list is None:
            signals_list = self._signal_names

        if isinstance(signals_list, StringTypes):
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
                    self._signal_type[self._signal_names.index(signal)] = max(self._all_types.values())
                else:
                    self._signal_type[self._signal_names.index(signal)] = 0

        self._fp.seek(0)
        # if skip_lines constructor parameter is not specified
        for _ in range(self._skip_lines + 1 + self._skip_data_lines):
            if PY2:
                self._csv.next()
            else:
                next(self._csv)

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
                raise self._exc('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))

        elif self._scan_opt == 'scan_auto':  # pylint: disable=R1702
            try:
                for _, row in enumerate(self._csv):
                    for signal in signals_list:
                        idx = self._signal_names.index(signal)
                        try:
                            data = str(row[idx])
                            if match(r"^(\d+)$", data.strip()) is not None:
                                val = int64(row[idx])
                            elif match(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?\s*\Z", data.strip()) is not None:
                                val = float(row[idx])
                            else:
                                val = data

                            if isinstance(val, StringTypes):
                                if match(r"[+]?1(\.)[#][Ii][Nn]", val.lstrip()) is not None:
                                    val = inf
                                elif match(r"-1(\.)[#][Ii][Nn]", val.lstrip()) is not None:
                                    val = -inf
                            self._signal_values[idx].append(val)
                            self._signal_type[idx] = max(self._all_types[type(val)], self._signal_type[idx])
                        except Exception as _:
                            self._signal_type[idx] = type(float)
                    # del row
            except Error as ex:
                raise self._exc('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))
        else:
            try:
                for row in self._csv:
                    for signal in signals_list:
                        idx = self._signal_names.index(signal)
                        self._signal_values[idx].append(self._scan_opt(row[idx]))
                for signal in signals_list:
                    idx = self._signal_names.index(signal)
                    self._signal_type[idx] = self._all_types[type(self._scan_opt(self._signal_values[idx][0]))]
            except Error as ex:
                raise self._exc('file %s, line %d: %s' % (self._file_path, self._csv.line_num, ex))


class BsigReader(object):  # pylint: disable=R0902
    """
    bsig reader class

    internal class used by SignalReader to read binary signal files (type bsig2 and bsig3)

    use class `SignalReader` to read files
    """

    def __init__(self, fp, **kwargs):  # pylint: disable=R0912,R0915
        """
        set default values

        :param str fp: file to use, can be a file pointer to an already open file or a name of file
        :param dict kwargs: see *SignalReader* class doc
        """
        self._arr_frmt = {0x0008: 'B', 0x8008: 'b', 0x0010: 'H', 0x8010: 'h', 0x0020: 'L', 0x8020: 'l', 0x0040: 'Q',
                          0x8040: 'q', 0x9010: 'f', 0x9020: 'd'}
        self._sig_frmt = {'c': 1, 'b': 1, 'B': 1, 'h': 2, 'H': 2, 'I': 4, 'l': 4, 'L': 4, 'q': 8, 'Q': 8,
                          'f': 4, 'd': 8}
        file_header = 24

        self._exc = kwargs["exc"]
        self._fp = fp
        self._npusage = kwargs.pop('use_numpy', True)
        self._name_sense = kwargs.pop('sensitive', True)
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
            if self._read_sig('c' * 4) != BSIG_HDR:
                raise self._exc("given file is not of type BSIG!")
            version = self._read_sig('B' * 3)
            if version[0] not in (2, 3):  # we support version 2 and 3 by now
                raise self._exc("unsupported version: %d.%d.%d, supporting only V2 & V3!" % version)
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
            if self._read_sig('c' * 4) != BSIG_FTR:  # bin signature
                raise self._exc("BSIG signature wrong!")

            # read signal description
            self._fp.seek(self._file_size - file_header - self._hdr_size)  # = self._hdr_offset
            for _ in range(signal_count):
                sig_name_len = self._read_sig('H')[0]
                signal_name = str("".join([i.decode() for i in self._read_sig('c' * sig_name_len)]))
                array_len, stype = self._read_sig('II')
                self._signal_data.append({SIG_NAME: signal_name, SIG_TYPE: stype, SIG_ARRAYLEN: array_len})

            # read offsets data
            self._fp.seek(self._file_size - file_header - self._hdr_size - offset_size)
            for sig in self._signal_data:
                offset_count, sig[SIG_SAMPLES] = self._read_sig('II')
                sig[SIG_OFFSET] = self._read_sig(self._offstype * offset_count)
        except self._exc:
            self.close()
            raise
        except Exception as _ex:
            self.close()
            raise self._exc("Error while reading signal information, corruption of data?")

    def close(self):
        """close signal file"""
        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None

                self._signal_data = None
            except Exception:
                raise self._exc("An error occurred while closing the file.")

    def __len__(self):
        """
        return number of signals in the binary file

        :return: number of signals in the binary file.
        :rtype: int
        """
        return len(self._signal_data)

    def __str__(self):
        """:return str: file info"""
        return "<bsig%d: '%s', signals: %d>" % (self._version, self._fp.name, len(self))

    def siglen(self, signal):
        """
        provide length of a signal, as csv's are of same length we do it the easy way

        :param str signal: name of signal
        :return: length of signal
        :rtype: int
        """
        if signal is None:
            return self._signal_data[0][SIG_SAMPLES]

        if self._name_sense:
            sigdet = next((s for s in self._signal_data if s[SIG_NAME] == signal), None)
        else:
            sigdet = next((s for s in self._signal_data if s[SIG_NAME].lower() == signal.lower()), None)
        if sigdet is None:
            raise self._exc("no signal by that name found: {!s}".format(signal))

        return sigdet[SIG_SAMPLES]

    def signal(self, signal, offset=None, count=None):  # pylint: disable=R0912,R1260
        """
        return data for signal with a specified index

        :param str signal: index / name of signal or list of the signals
        :param int offset: data offset of signal
        :param count count: length of data
        :return: signal data as an array (default) or list as defined during reader initialisation
        :rtype: array or list
        """
        # check for input argument validity
        if isinstance(signal, (tuple, list)):
            return [self.signal(s) for s in signal]
        if isinstance(signal, int) and 0 <= signal < len(self._signal_data):
            sigdet = self._signal_data[signal]
        else:
            if self._name_sense:
                sigdet = next((s for s in self._signal_data if s[SIG_NAME] == signal), None)
            else:
                sigdet = next((s for s in self._signal_data if s[SIG_NAME].lower() == signal.lower()), None)
            if sigdet is None:
                raise self._exc("signal not found: %s" % signal)

        # align offset and count, count is initially the length, but we use it as stop point and offset as start point
        if offset is None:
            offset = 0
        elif offset < 0:
            offset = sigdet[SIG_SAMPLES] + offset
        if count is None:
            count = sigdet[SIG_SAMPLES]
        elif count < 0 or offset + count > sigdet[SIG_SAMPLES]:
            raise self._exc("offset / count for signal {} is out of range: {!s} / {!s}".format(signal, offset, count))
        else:
            count += offset

        frmt = self._arr_frmt[sigdet[SIG_TYPE]]  # data format
        dlen = self._sig_frmt[frmt]  # length of one data point
        blkl = self._block_size // dlen  # real block length
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

            data = unpack(frmt * (len(data) // dlen), data)
            sig.extend(data)

        if self._npusage:
            if alen == 1:
                return array(sig[offset:count], dtype=frmt)
            return array(sig[offset:count], dtype=frmt).reshape(((count - offset) // alen, alen))

        if alen == 1:
            return sig[offset:count]
        return [sig[i:i + alen] for i in range(offset, count, alen)]

    @property
    def signal_names(self):
        """
        return names of all signals with the specified index.

        :return: all signal names in file
        :rtype: list
        """
        return [sig[SIG_NAME] for sig in self._signal_data]

    def _read_sig(self, stype):
        """read signal of given type"""
        try:
            return unpack(stype, self._fp.read(self._sig_frmt[stype[0]] * len(stype)))
        except Exception:
            raise self._exc("An error occured while reading binary data.")


class SignalReader(object):
    r"""**MAIN Class for Signal File Read.** (\*.bsig (aka \*.bin), \*.csv)"""

    def __init__(self, filename, **kwargs):
        r"""
        open the binary file by its name, supported formats: bsig 2, 3, csv

        :param str filename: path/to/file.name
        :param dict kwargs: see below

        :keyword \**kwargs:
            * *type* (``str``): type of file can set explicitly, set to 'bsig' will force it to be a bsig

        *following parameter can be used when intending to open e.g. a bsig file.*

        :keyword \**kwargs:
            * *use_numpy* (``bool``): whether using numpy arrays for signal values, default: True
            * *sensitive* (``bool``): whether to treat signal names case sensitive, default: True

        *following parameter can be used when intending to open e.g. a csv file.*

        :keyword \**kwargs:
            * *delim* (``str``): delimiter char for columns
            * *scan_type* (``str``): can be `no_prefetch` or `prefetch` to read in data at init
            * *scan_opt* (``str``): can be `scan_auto`, 'scan_raw' or e.g. 'float', 'int' or 'str'
            * *scip_lines* (``int``): how many lines should be scripped / ignored reading in at start of file
            * *scip_data_lines* (``int``): how many lines of data should be scripped reading in at start
        """
        self._exc = kwargs["exc"]
        self._fp = filename

        if kwargs.pop('type', "bsig") == 'bsig' and \
                splitext(self._fp.name if hasattr(self._fp, 'read')
                         else filename)[1].lower() in ('.bsig', '.bin', '.tstp'):
            self._reader = BsigReader(self._fp, **kwargs)
            self._type = "bsig"
        else:
            self._reader = CsvReader(self._fp, **kwargs)
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
        """:return str: the type and number of signals"""
        return str(self._reader)

    def __len__(self):
        """return number of signals from reader"""
        return len(self._reader)

    def signal_length(self, signal=None):
        """
        length of a signal

        :param str signal: name of signal length should be returned
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

        self._iter_idx += 1
        return self._signal_names[self._iter_idx - 1], self[self._iter_idx - 1]

    if PY3:
        __next__ = next

    def __contains__(self, name):
        """
        check if signal name is stored in SignalReader

        :param str name: signal name to check
        :return: wether signal is contained or not
        :rtype: bool
        """
        return name in self._signal_names

    def __getitem__(self, signal):
        """
        provide signal by name or index,

        if index is a slice use start as index,
        stop as offset and step as count

        :param signal: signal name or index or sliced index
        :type  signal: str, int, tuple/list
        :return:  signal with type as defined in reader initiation
        :rtype:   array or list
        :raises IndexError: once idx is out of range
        """
        # [Offset:Offset + SampleCount]
        try:
            if isinstance(signal, (int, StringTypes)):
                return self._reader.signal(signal)
            if isinstance(signal, (tuple, list)):
                if set(signal).issubset(self._signal_names):
                    return self._reader.signal(signal)

                return self._reader.signal(signal[0], signal[1], signal[2])
            if isinstance(signal, slice):  # not nice, but no other strange construct needed
                return self._reader.signal(signal.start, signal.stop, signal.step)

            raise IndexError
        except (IndexError, self._exc):
            raise
        except Exception as _:
            raise self._exc("Data corruption inside signal file, unable to read signal '{}'!".format(signal))

    @property
    def signal_names(self):
        """
        list of all signal names

        :return: all signal names in file
        :rtype:  list
        """
        return self._signal_names
