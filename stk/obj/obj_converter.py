"""
obj_converter.py
----------------

Object converter to read and convert signal objects in one step

The `ObjConverter` is an extension of the `SignalLoader`. It allowes to define groups of signal objects
to read and convert together.

To configure the block of signals it follows the config of the `SignalExtractor` in `Valf` package.
The same structure as for signal definitions in the SignalExtractor can be used here,
and as extension to the SignalLoader this converter method also uses the port names.

Port names are used as keys in the returned dictionary::





:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/10/25 12:20:07CEST $
"""
# pylint: disable=E1101,E0203,W0201
# - Python imports ----------------------------------------------------------------------------------------------------
from numpy import zeros, int as nint

# - STK imports -------------------------------------------------------------------------------------------------------
from stk.io.signalreader import SignalReaderException


# - classes -----------------------------------------------------------------------------------------------------------
class ObjConverter(object):
    """object converter to convert raw signals from signal_loader to objects as being done by signal extractor.
    """

    def __init__(self, **kwargs):
        """some things need to be set up

        kwargs are set directly to private variables (with underscore prefixed)

        :keyword min_lifetime: minimum lifetime of an object
        """
        # set defaults
        self.__dict__.update({'_min_life': 10, '_timestamp': None,
                              '_aoj_list_size': None, '_aoj_mapping': None,
                              '_aoj_prefix': '', '_aoj_signals': []})

        # overwrite with argument provided changes
        for k, v in kwargs.iteritems():
            setattr(self, "_" + k, v)

        for sig in self._aoj_signals:
            if sig['name'].startswith('.'):
                sig['name'] = self._aoj_prefix + sig['name']

        # set other internals
        self._loader = None
        self._indices = []

    def xinit(self, loader, *args):
        """extra inits before loader starts iteration

        :param loader: signal reader instance
        :param args: provided arguments from signal loader
        """
        self._loader = loader
        blidx = 0

        # for speed reasons, we extract the additional object lists
        if self._aoj_mapping:
            signame, i = self._aoj_mapping.replace('%', '%d'), 0
            self._aoj_mapping = []
            while True:
                try:
                    self._aoj_mapping.append(loader._bsig[signame % i])
                    i += 1
                except SignalReaderException:
                    break

        # also, take timestamp signal
        if self._timestamp:
            self._timestamp = loader._bsig[self._timestamp]

        while True:
            sig = args[0].replace('%', '%d' % blidx)
            try:
                sig = loader._bsig[sig]
            except SignalReaderException:
                break

            start_pos, life_time = 0, 0

            for k in xrange(start_pos, len(sig)):
                if sig[k] in (1, 5):
                    if life_time == 0:
                        start_pos = k
                        life_time += 1
                    else:
                        if life_time >= self._min_life:
                            self._indices.append((start_pos, life_time, blidx))
                        life_time = 0
                elif sig[k] in (2, 3):
                    life_time += 1
                elif sig[k] in (0, 4):
                    if life_time != 0:
                        if life_time >= self._min_life:
                            self._indices.append((start_pos, life_time, blidx))
                        life_time = 0

            if life_time >= self._min_life:
                self._indices.append((start_pos, life_time, blidx))

            blidx += 1

        self._indices.sort()

        return True, len(self._indices)

    def conv(self, idx, signals):
        """convert, I mean, extract object at index using sigs

        :param idx: global index of object
        :param signals: list of signals to process
        :return: dict(key: <port>, value: <object>)
        """
        det = self._indices[idx]
        obj = {"ObjectId": idx, "Index": det[0], "StartTime": self._timestamp[det[0]],
               "Timestamp": self._timestamp[det[0]:det[0] + det[1]],
               "OOIHistory": [], "Relevant": zeros(det[1], dtype=nint),
               "fDistXAbs": [], "fDistYAbs": []}

        for sig in signals:
            obj[sig['port']] = self._loader._bsig[sig['name'].replace('%', str(det[2])):det[0]:det[1]]
            if self._aoj_mapping:  # retrieve additional object list
                map_idx = self._aoj_mapping[det[2]][det[0]]
                if 0 <= map_idx < self._aoj_list_size:
                    for asig in self._aoj_signals:
                        obj[asig['port']] = self._loader._bsig[asig['name'].replace('%', str(map_idx)):det[0]:det[1]]

        for pos in xrange(det[0], det[0] + det[1]):
            if pos > 10 and det[2] == 255:
                obj["Relevant"][pos - det[0]] = 1

        return obj


"""
CHANGE LOG:
-----------
$Log: obj_converter.py  $
Revision 1.3 2016/10/25 12:20:07CEST Hospes, Gerd-Joachim (uidv8815) 
add ObjSignals class with tests and docu
Revision 1.2 2015/06/26 11:34:33CEST Mertens, Sven (uidv7805)
pep8 fixes
- Added comments -  uidv7805 [Jun 26, 2015 11:34:33 AM CEST]
Change Package : 338364:2 http://mks-psad:7002/im/viewissue?selection=338364
Revision 1.1 2015/06/26 09:42:38CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
"""
