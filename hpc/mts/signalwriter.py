"""
signalwriter.py
---------------

signal writer class
"""
from __future__ import division

__all__ = ['SignalWriter']

# - import Python modules ----------------------------------------------------------------------------------------------
from os.path import splitext
from struct import pack
from zlib import compress
from csv import DictWriter
from six import iteritems, PY2

# - import HPC modules -------------------------------------------------------------------------------------------------
from . import BSIG_HDR, BSIG_FTR, StringTypes, SIG_NAME, SIG_TYPE, SIG_ARRAYLEN, SIG_OFFSET, SIG_SAMPLES


# - classes ------------------------------------------------------------------------------------------------------------
class CsvWriter(object):
    """CSV writer class"""

    def __init__(self, fp, **xargs):
        """
        set default values

        :param str fp: file or file pointer to write to
        :param xargs: extra arguments to csv.DictWriter()
        """
        self._fp = fp
        self._exc = xargs.pop("exc")
        self._xargs = xargs

        if not hasattr(self._fp, 'write'):
            self._selfopen = True
            try:
                self._fp = open(self._fp, "wb" if PY2 else "w")
            except Exception:
                raise self._exc("Error while trying to open file, corrupted?")
        else:
            self._selfopen = False

        self._signal_data = None
        self._len = 0

    def append(self, name, signal):
        """
        add a signal, being a numpy array

        :param str name: name of signal
        :param numpy.array signal: signal to be added
        """
        if self._len == 0:
            self._len = len(signal)
            self._signal_data = [{} for _ in range(self._len)]
        elif self._len != len(signal) or signal[0].size > 1:
            raise self._exc("signals are not of same length or shape!")

        for i in range(self._len):
            self._signal_data[i][name] = signal[i]

    def close(self):
        """finishes up file write operation"""
        if self._len == 0:
            return
        writer = DictWriter(self._fp, list(self._signal_data[0].keys()),
                            delimiter=self._xargs.pop('delim', ';'), **self._xargs)
        writer.writeheader()
        writer.writerows(self._signal_data)

        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None
            except Exception:
                raise self._exc("An error occured while closing the file.")

    def __str__(self):
        """:return str: file info"""
        return "<dlm: '%s', signals: %d>" % (self._fp.name, len(self._signal_data[0]) if self._len else 0)

    @property
    def signal_names(self):
        """:return str: all names which are known at a time in a list"""
        return list(self._signal_data[0].keys()) if self._len else []


class BsigWriter(object):
    """bsig writer class"""

    def __init__(self, fp, **kwargs):
        """
        open a bsig for writing

        :param str fp: file to use, can be a file pointer to an already open file or a name of file
        :param dict kwargs: please see SignalWriter doc
        """
        self._fp = fp
        self._exc = kwargs.pop("exc")
        self._sig_frmt = {'b': 32776, 'h': 32784, 'l': 32800, 'B': 8, 'H': 16,
                          'L': 32, 'q': 32832, 'Q': 64, 'f': 36880, 'd': 36896}

        # valid values: 2^12 ... 2^16
        self._block_size = kwargs.pop('block_size', 4096)
        assert self._block_size in (2 ** i for i in range(8, 17)), "block_size wrong!"
        self._v2 = kwargs.pop('v2format', False)
        assert isinstance(self._v2, bool), "type of v2format wrong!"
        self._signal_data = []

        if not hasattr(self._fp, 'write'):
            self._selfopen = True
            try:
                self._fp = open(self._fp, "wb")
            except Exception:
                raise self._exc("Error while trying to open file, corrupted?")
        else:
            self._selfopen = False

        # write global header
        self._write_sig('c', BSIG_HDR)
        self._write_sig('B', [2 if self._v2 else 3, 0, 0, 0])

        # add name and signal immediatelly now.
        for name, sdata in iteritems(kwargs.pop('sigdict', {})):
            self.append(name, sdata)

    def append(self, name, signal):
        """
        add a signal, being a numpy array

        :param str name: name of signal
        :param numpy.array signal: signal to be added
        """
        signal_len = len(signal)
        array_len = signal[0].size if signal_len > 0 else 0
        if array_len > 1:
            signal = signal.flatten()

        offsets = []
        i = 0
        block_sz = self._block_size // signal.dtype.itemsize  # self._sigfrmt[signal.dtype.char][1]
        while i < len(signal):
            data = [pack(signal.dtype.char, d) for d in signal[i:i + block_sz]]
            if PY2:
                data = ''.join(data)
            else:
                data = b''.join(data)
            data = compress(data)
            offsets.append(self._fp.tell())
            self._write_sig('I', len(data))
            self._fp.write(data)
            i += block_sz

        self._signal_data.append({SIG_NAME: name, SIG_SAMPLES: signal_len, SIG_ARRAYLEN: array_len,
                                  SIG_OFFSET: offsets, SIG_TYPE: signal.dtype.char})

    def close(self):
        """finish up file write operation"""
        # write offsets
        offset = self._fp.tell()
        for signal in self._signal_data:
            self._write_sig('I', [len(signal[SIG_OFFSET]), signal[SIG_SAMPLES]])
            self._write_sig('L' if self._v2 else 'Q', signal[SIG_OFFSET])
        offset = self._fp.tell() - offset

        # write signal desc
        header = self._fp.tell()
        for signal in self._signal_data:
            self._write_sig('H', len(signal[SIG_NAME]))
            self._write_sig('c', signal[SIG_NAME] if PY2 else [bytes(i, 'utf-8') for i in signal[SIG_NAME]])
            self._write_sig('I', [signal[SIG_ARRAYLEN], self._sig_frmt[signal[SIG_TYPE]]])  # array length & type
        header = self._fp.tell() - header

        # write file header
        self._write_sig('I', [len(self._signal_data), self._block_size, header, offset])
        self._write_sig('B', [0, 0, 0, 1])  # write internal version (unused) & compression flag
        self._write_sig('c', BSIG_FTR)

        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None
            except Exception:
                raise self._exc("An error occured while closing the file.")

    def __str__(self):
        """:return str: file info"""
        return "<bsig3: '%s', signals: %d>" % (self._fp.name, len(self._signal_data))

    @property
    def signal_names(self):
        """:return list: all signal names which are known in a list"""
        return [s[SIG_NAME] for s in self._signal_data]

    def _write_sig(self, stype, data):
        """write packed signal data of given type"""
        try:
            if isinstance(data, (list, tuple, StringTypes)):
                for d in data:
                    self._fp.write(pack(stype, d))
            else:
                self._fp.write(pack(stype, data))
        except Exception as _ex:
            raise self._exc("An error occured while unpacking binary data.")


class SignalWriter(object):
    r"""
    MAIN Class for Signal File Write. (\\*.bsig)

    Example 1::

        import numpy as np
        from hpc import Signal, SignalException

        # EXAMPLE 1 (just write some)
        with Signal('file_hla_xyz.bsig', mode='w') as sw:
            sw.append('Time stamp', np.array([0, 1, 2, 3, 4, 5, 6, 7]))
            sw.append('Cycle counter', np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))

    EXAMPLE 2::

        # reorganize
        bsig_in_file, bsig_out_file = 'Snapshot_201x.x.y_at_h.m.s_FCT.bsig', 'Snapshot_201x.x.y_at_h.m.s_all.bsig'
        sig_list = ['MTS.Timestamp', 'MTS.Cyclecounter', 'SIM VFB.FCTVehicle.HEAD.Header.uiStructSize', ...]

        with Signal(bsig_in_file) as sin, Signal(bsig_out_file, mode='w') as sout:
            for sig in sig_list:
                sout.append(sig, sin[sig])

    EXAMPLE 3::

        # CSV
        with Signal('Snapshot_xyz.csv', mode='w') as sw:
            sw.append('signal 1', np.array([0, 1, 2, 3, 4, 5, 6, .....]))
            ...

    """

    def __init__(self, filename, **kwargs):
        r"""
        open the binary file by its name, supported formats: bsig2, csv, txt

        :param str filename: path/to/file.name
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *type* (``str``): type of file can set explicitly, set to 'bsig' will force it to be a bsig
            * *v2format* (``bool``): used by bsig writer to force format to 2nd version
            * *sigdict* (``dict``): signal dictionary to immediatelly write
            * *block_size* (``int``): set buffer block size of bsigs, default: 4096 (4kb)
        """
        self._fp = filename
        ftype = kwargs.pop('type', None)

        if splitext(self._fp.name if hasattr(self._fp, 'write')
                    else filename)[1].lower() in ('.bsig', '.bin', '.tstp') or ftype == 'bsig':
            self._writer = BsigWriter(self._fp, **kwargs)
        elif splitext(self._fp.name if hasattr(self._fp, 'write')
                      else filename)[1].lower() == '.csv' or ftype == 'csv':
            self._writer = CsvWriter(self._fp, **kwargs)
        else:
            raise kwargs["exc"]("unsupported file format, you can force one !")

    def __enter__(self):
        """being able to use with statement"""
        return self

    def __exit__(self, *_):
        """close down file"""
        self._writer.close()

    def close(self):
        """close file"""
        self._writer.close()

    def __str__(self):
        """:return str: the type and number of signals"""
        return str(self._writer)

    def append(self, name, signal):
        """
        append a signal to file, numpy array required!

        :param str name: name of signal to be added
        :param numpy.array signal: signal to be added
        """
        self._writer.append(name, signal)

    @property
    def signal_names(self):
        """:return list: all signal names which are known in a list"""
        return self._writer.signal_names
