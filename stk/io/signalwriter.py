"""
stk/io/signalwriter
-------------------

Signal Writer Class

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.10 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/07/11 16:42:55CEST $
"""

__all__ = ['SignalWriter', 'SignalWriterException']

# - import Python modules ---------------------------------------------------------------------------------------------
from os import path as opath
from struct import pack
from zlib import compress
from csv import DictWriter

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.error import StkError

# - defines -----------------------------------------------------------------------------------------------------------
SIG_NAME = 'SignalName'
SIG_TYPE = 'SignalType'
SIG_ARRAYLEN = 'ArrayLength'
SIG_OFFSET = 'Offsets'
SIG_SAMPLES = 'SampleCount'


# - classes -----------------------------------------------------------------------------------------------------------
class SignalWriterException(StkError):
    """general exception for SignalReader class"""
    def __init__(self, msg):
        """derived from std error"""
        delim = "\n=" * (len(msg) + 7) + "\n"
        StkError.__init__(self, "%sERROR: %s%s" % (delim, msg, delim))


class CsvWriter(object):
    """CSV writer class
    """
    def __init__(self, fp, **xargs):
        """set default values

        :param fp: file or file pointer to write to
        :param xargs: extra arguments to csv.DictWriter()
        """
        self._fp = fp
        self._xargs = xargs

        if not hasattr(self._fp, 'write'):
            self._selfopen = True
            try:
                self._fp = open(self._fp, "wb")
            except:
                raise SignalWriterException("Error while trying to open file, corrupted?")
        else:
            self._selfopen = False

        self._signal_data = None
        self._len = 0

    def append(self, name, signal):
        """add a signal, being a numpy array

        :type name: name of signal
        :param signal: signal to be added
        :type signal: list | narray
        """
        if self._len == 0:
            self._len = len(signal)
            self._signal_data = [{} for _ in xrange(self._len)]
        elif self._len != len(signal) or signal[0].size > 1:
            raise SignalWriterException("signals are not of same length or shape!")

        for i in xrange(self._len):
            self._signal_data[i][name] = signal[i]

    def close(self):
        """finishes up file write operation
        """
        if self._len == 0:
            return
        writer = DictWriter(self._fp, self._signal_data[0].keys(),
                            delimiter=self._xargs.pop('delim', ';'), **self._xargs)
        writer.writeheader()
        writer.writerows(self._signal_data)

        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None
            except:
                raise SignalWriterException("An error occured while closing the file.")

    def __str__(self):
        """:return: file info"""
        return "<dlm: '%s', signals: %d>" % (self._fp.name, len(self._signal_data[0]) if self._len else 0)

    @property
    def signal_names(self):
        """returns all names which are known at a time in a list
        """
        return self._signal_data[0].keys() if self._len else []


class BsigWriter(object):
    """bsig writer class
    """
    def __init__(self, fp, **kwargs):
        """set default values

        :param fp: file to use, can be a file pointer to an already open file or a name of file
        :keyword v2format: set to True to let bsig writer use older v2 format instead of v3
        :type v2format: bool
        :keyword block_size: block size to write bsig with
        :type block_size: int
        :keyword sigdict: dictionary of signals to write
        """
        self._fp = fp
        self._sig_frmt = {'b': 32776, 'h': 32784, 'l': 32800, 'B': 8, 'H': 16,
                          'L': 32, 'q': 32832, 'Q': 64, 'f': 36880, 'd': 36896}

        # valid values: 2^12 ... 2^16
        self._block_size = kwargs.pop('block_size', 4096)
        assert self._block_size in (2 ** i for i in xrange(8, 17)), "block_size wrong!"
        self._v2 = kwargs.pop('v2format', False)
        assert type(self._v2) == bool, "type of v2format wrong!"
        self._signal_data = []

        if not hasattr(self._fp, 'write'):
            self._selfopen = True
            try:
                self._fp = open(self._fp, "wb")
            except:
                raise SignalWriterException("Error while trying to open file, corrupted?")
        else:
            self._selfopen = False

        # write global header
        self._write_sig('c', "BSIG")
        self._write_sig('B', [2 if self._v2 else 3, 0, 0, 0])

        # add name and signal immediatelly now.
        for name, sdata in kwargs.pop('sigdict', {}).iteritems():
            self.append(name, sdata)

    def append(self, name, signal):
        """add a signal, being a numpy array

        :type name: name of signal
        :param signal: signal to be added
        :type signal: list | narray
        """
        signal_len = len(signal)
        array_len = signal[0].size if signal_len > 0 else 0
        if array_len > 1:
            signal = signal.flatten()

        offsets = []
        i = 0
        block_sz = self._block_size / signal.dtype.itemsize  # self._sigfrmt[signal.dtype.char][1]
        while i < len(signal):
            data = compress("".join([pack(signal.dtype.char, d) for d in signal[i:i + block_sz]]))
            offsets.append(self._fp.tell())
            self._write_sig('I', len(data))
            self._fp.write(data)
            i += block_sz

        self._signal_data.append({SIG_NAME: name, SIG_SAMPLES: signal_len, SIG_ARRAYLEN: array_len,
                                  SIG_OFFSET: offsets, SIG_TYPE: signal.dtype.char})

    def close(self):
        """finishes up file write operation
        """
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
            self._write_sig('c', signal[SIG_NAME])
            self._write_sig('I', [signal[SIG_ARRAYLEN], self._sig_frmt[signal[SIG_TYPE]]])  # array length & type
        header = self._fp.tell() - header

        # write file header
        self._write_sig('I', [len(self._signal_data), self._block_size, header, offset])
        self._write_sig('B', [0, 0, 0, 1])  # write internal version (unused) & compression flag
        self._write_sig('c', 'BIN\x00')

        if self._fp is not None:
            try:
                if self._selfopen:
                    self._fp.close()
                self._fp = None
            except:
                raise SignalWriterException("An error occured while closing the file.")

    def __str__(self):
        """returns file info"""
        return "<bsig3: '%s', signals: %d>" % (self._fp.name, len(self._signal_data))

    @property
    def signal_names(self):
        """returns all signal names which are known in a list
        """
        return [s[SIG_NAME] for s in self._signal_data]

    def _write_sig(self, stype, data):
        """write packed signal data of given type
        """
        try:
            if type(data) in (list, tuple, str):
                for d in data:
                    self._fp.write(pack(stype, d))
            else:
                self._fp.write(pack(stype, data))
        except:
            raise SignalWriterException("An error occured while unpacking binary data.")


class SignalWriter(object):
    """
    MAIN Class for Signal File Write. (\\*.bsig)

    usage (example)
    ---------------

    .. python::
        reader = SignalReader('file_path')

    *Examples*

    .. python::
        import numpy as np
        from stk.io.signalwriter import SignalWriter, SignalWriterException

        # EXAMPLE 1 (just write some)
        with SignalWriter('file_hla_xyz.bsig') as sw:
            sw.append('Time stamp', np.array([0, 1, 2, 3, 4, 5, 6, 7]))
            sw.append('Cycle counter', np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32))

        # EXAMPLE 2 (reorganize)
        bsig_in_file, bsig_out_file = 'Snapshot_201x.x.y_at_h.m.s_FCT.bsig', 'Snapshot_201x.x.y_at_h.m.s_all.bsig'
        sig_list = ['MTS.Timestamp', 'MTS.Cyclecounter', 'SIM VFB.FCTVehicle.HEAD.Header.uiStructSize', ...]

        with SignalReader(bsig_in_file) as sin, SignalWriter(bsig_out_file) as sout:
            for sig in sig_list:
                sout.append(sig, sin[sig])

        # EXAMPLE 3 (CSV)
        with SignalWriter('Snapshot_xyz.csv') as sw:
            sw.append('signal 1', np.array([0, 1, 2, 3, 4, 5, 6, .....]))
            ...

    """

    def __init__(self, filename, **kwargs):
        """open the binary file by its name, supported formats: bsig2, csv, txt

        parameters:
          ``v2format``: set to True to let BsigWriter use older v2 format instead of v3 (bool)
          ``block_size``: set buffer block size of bsigs, default: 4096 (4kb)
          ``type``: type of signal format, supported: bsig, csv (str)

        :param filename: path/to/file.name
        :type filename: str
        :keyword type: csv or bsig as being the forced type
        :keyword v2format: used by bsig writer to force format to 2nd version
        :keyword sigdict: signal dictionary to immediatelly write
        """
        self._fp = filename
        ftype = kwargs.pop('type', None)

        if opath.splitext(self._fp.name if hasattr(self._fp, 'write')
                          else filename)[1].lower() in ('.bsig', '.bin', '.tstp') or ftype == 'bsig':
            self._writer = BsigWriter(self._fp, **kwargs)
        elif opath.splitext(self._fp.name if hasattr(self._fp, 'write')
                            else filename)[1].lower() == '.csv' or ftype == 'csv':
            self._writer = CsvWriter(self._fp, **kwargs)
        else:
            raise SignalWriterException("unsupported file format, you can force one !")

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
        """returns the type and number of signals"""
        return str(self._writer)

    def append(self, name, signal):
        """append a signal to file, numpy array required!

        :type name: name of signal to be added
        :param signal: signal to be added
        :type signal: narray
        """
        self._writer.append(name, signal)

    @property
    def signal_names(self):
        """returns all signal names which are known in a list
        """
        return self._writer.signal_names


"""
CHANGE LOG:
-----------
$Log: signalwriter.py  $
Revision 1.10 2016/07/11 16:42:55CEST Mertens, Sven (uidv7805) 
fix for zero length signals
Revision 1.9 2016/03/29 17:39:23CEST Mertens, Sven (uidv7805)
pylint
Revision 1.8 2015/11/02 10:16:43CET Mertens, Sven (uidv7805)
support for signals with different length added
--- Added comments ---  uidv7805 [Nov 2, 2015 10:16:44 AM CET]
Change Package : 355671:2 http://mks-psad:7002/im/viewissue?selection=355671
Revision 1.7 2015/06/30 11:10:53CEST Mertens, Sven (uidv7805)
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:10:53 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.6 2015/06/26 09:36:04CEST Mertens, Sven (uidv7805)
default buffer size seems to be 4k
--- Added comments ---  uidv7805 [Jun 26, 2015 9:36:04 AM CEST]
Change Package : 338364:2 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.5 2015/06/25 11:54:08CEST Mertens, Sven (uidv7805)
another pep8 fix
--- Added comments ---  uidv7805 [Jun 25, 2015 11:54:08 AM CEST]
Change Package : 350659:2 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.4 2015/06/25 11:45:20CEST Mertens, Sven (uidv7805)
pep8 fix
--- Added comments ---  uidv7805 [Jun 25, 2015 11:45:20 AM CEST]
Change Package : 350659:2 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.3 2015/06/24 16:36:11CEST Mertens, Sven (uidv7805)
removing not
--- Added comments ---  uidv7805 [Jun 24, 2015 4:36:11 PM CEST]
Change Package : 350659:1 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.2 2015/06/02 10:02:25CEST Mertens, Sven (uidv7805)
support for different block sizes added
--- Added comments ---  uidv7805 [Jun 2, 2015 10:02:25 AM CEST]
Change Package : 338364:1 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.1 2015/04/23 19:04:31CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
Revision 1.9 2015/04/08 14:10:29CEST Mertens, Sven (uidv7805)
escape properly
--- Added comments ---  uidv7805 [Apr 8, 2015 2:10:29 PM CEST]
Change Package : 318014:1 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.8 2015/04/08 10:12:27CEST Mertens, Sven (uidv7805)
docu update
Revision 1.7 2015/04/07 16:52:24CEST Mertens, Sven (uidv7805)
docu update
Revision 1.6 2015/02/26 16:13:04CET Mertens, Sven (uidv7805)
docu update
Revision 1.5 2015/02/10 08:24:12CET Mertens, Sven (uidv7805)
mks!
--- Added comments ---  uidv7805 [Feb 10, 2015 8:24:12 AM CET]
Change Package : 304708:1 http://mks-psad:7002/im/viewissue?selection=304708
Revision 1.4 2015/02/10 08:23:16CET Mertens, Sven (uidv7805)
provide a csv writer extention
--- Added comments ---  uidv7805 [Feb 10, 2015 8:23:16 AM CET]
Change Package : 304708:1 http://mks-psad:7002/im/viewissue?selection=304708
Revision 1.3 2015/01/30 08:29:26CET Mertens, Sven (uidv7805)
add support for bsig version 2
Revision 1.2 2015/01/22 11:05:03CET Mertens, Sven (uidv7805)
adaptation to wrong indexing if negative
Revision 1.1 2015/01/13 16:34:59CET Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/io/project.pj
"""
