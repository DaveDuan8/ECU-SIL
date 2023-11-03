r"""
signal_loader.py
----------------

Used to load and convert signals or block of signals.

The `SignalLoader` is the extension of the `SignalReader` to combine several signals and read them together.

**Configuration**

To configure the block of signals to load it follows the config of the `SignalExtractor` in `Valf` package.
The same structure as for signal definitions in the SignalExtractor can be used here,
but only the 'name' element is read by the SignalLoader.

Arguments to class initialization look like this::

  vdy={'prefix': 'SIM VFB ALL.DataProcCycle.ObjSyncEgoDynamic',
       'signals': [{'name': '.Lateral.Curve.Curve'},
                   {'name': '.Longitudinal.MotVar.Velocity'},
                   {'name': '.Longitudinal.MotVar.Accel'},
                   {'name': '.Lateral.YawRate.YawRate'}
                  ]
      }

Supported keywords in the signal block structure:

prefix:
    whereas ``prefix`` will prepend the names from list of signals (default: '').
    **The prefix will only be added if the signal name starts with a ".".**
    This allows to add signals with different path than defined in the prefix,
    e.g. adding ``MTS.Package.Timestamp`` signal to the above ``vdy`` block.

signals:
    list of dicts with 'name' key providing the signal name,
    the dict can contain more key/value pairs, so it's possible to pass directly
    the configuration of the SignalExtractor.

conv:
    The conversion function ``conv`` is called with the extracted signal,
    the default function just returns the signal: ``'conv': lambda s: s``::

        def sigconv(sig):
            return max(sig)

        sl = SignalLoader(join(DATAPATH, "Continuous_2014.05.06_at_11.14.13.bsig"),
                          reader={'use_numpy': False,
                                  'sensitive': False},
                          convdef={'prefix': 'MTS.Package',
                                   'signals': [{'name': '.TimeStamp'},
                                               {'name': '.CycleCount'},
                                               {'name': '.CycleID'}],
                                   'conv': sigconv})
        tme_max = sl('convdef')[0]

iter:
    The iteration function and its arguments. This method is called during initialisation
    to define the length of the returned list and prepare possible class vars used in
    an own conv method.
    It gets the SignalLoader instance and the defined arguments as parameters::

        def sigiter(loader, *args):
            return False, 2  # no own conv (use default here), two signals in block

        sl = SignalLoader(join(DATAPATH, "Continuous_2014.05.06_at_11.14.13.bsig"),
                          iterdef={'signals': [{'name': 'MTS.Package.TimeStamp'},
                                               {'name': 'MTS.Package.CycleCount'}],
                                   'iter': {'func': sigiter,
                                            'args': 42, ['TimeStamp', 'CycleCount']}})

    A more complex iteration can be found in `stk.obj.obj_converter.py` creating indices
    for all found active objects in the signal.

reader:
    Pass additional options to the used `SignalReader` class to e.g. return lists instead of numpy arrays::

        'reader': {'use_numpy': False},

    Options are passed as key value of a dict, possible SignalReader options find at `SignalReader.__init__`.

The provided class `ObjSignals` can be used to extract a set of signals using an index marker,
see the docu there for details about initialisation::

  'signals': [{'name': 'CDInternalObjInfo.Obj[%].TTC'}, ...

Iteration will then go along all indices found. If you want to use less, you need to keep track outside,
e.g. with your own counter (see 'idx' variable in example 2).

**Returns**

Output of the SignalLoader is a list of signals ordered as they are configured::

  sl('vdy')[0]  # get first signal of vdy


**Be aware that the default return type of the SignalReader is a numpy array.**
To get lists of values for each signal add the needed SignalReader parameters using keyword ``reader``::

    'reader': {'use_numpy': False},

All parameters defined for the 'reader' keyword will be passed to the used SignalReader
to get it initialised as expected.

The returned list of signals can be accessed by calling the SignalLoader instance
with the block name and the index for the signal, or using the provided iterator.


**example 1**
-------------

read out simple list of signals as numpy arrays::

  sl = SignalLoader(r'D:\tmp\Continuous_2015.04.22_at_12.15.53.bsig',
                    fixed={'prefix': 'MTS.Package.',
                           'signals': [{'name': 'TimeStamp'}, {'name': 'CycleCount'}],
                           'conv': lambda s: s   # default
                          },
                    ars={'signals': [{'name': 'ARS4xx Device.AlgoVehCycle.VehDyn.Longitudinal.MotVar.Velocity'},
                                     {'name': 'MTS.Package.TimeStamp'}
                                    ]})
  for i in sl('fixed'):
      print(i)

  print("do we have 'var': %s" % ('var' in sl))  # prints: .... False as only ``fixed`` and ``ars`` was defined

  cyc = sl('ars')[1]  # reads ``Velocity`` signal (second in configured list) as numpy array

  sl.close()

Here the ``sl('fixed')[0]`` and ``sl('ars')[1]`` contain same signal ``TimeStamp``
(showing different configuration).

**example 2**
-------------

block readout of object signals using `ObjSignals`, return signals as lists of values::

    obj_sigs = ObjSignals()

    with SignalLoader(join(DATAPATH, "Continuous_2014.05.06_at_11.14.13.bsig"),
                      reader={'use_numpy': False},
                      obj={'prefix': 'SIM VFB ALL.DataProcCycle.EmGenObjectList',
                           'signals': [{'name': '.aObject[%].General.uiLifeCycles'},
                                       {'name': '.aObject[%].Kinematic.fDistX'},
                                       {'name': '.aObject[%].Kinematic.fDistY'}],
                           'conv': obj_sigs.get_sig,
                           'iter': {'func': obj_sigs.xinit,
                                    'args': self}}
                      ) as sl:

        for idx, sig in enumerate(sl('obj')):
            # sig : [ [<uiLifeCycles>], [<fDistX>)], [<fDistY>] ]
            rel_dist_coord = [(sig[1][j], sig[2][j]) for j in xrange(len(sig[0]))]
            if idx > 5:
                break  # extract only first object signals as an example

**Tips**

Performance
-----------

The SignalLoader creates a SignalReader instance which reads the passed file in the beginning
to get the sizes, internal offset etc. If several blocks of signals are needed from the same file
these should be defined in one SignalLoader instance to use and start only one reader instance.

Additional signals that are not defined in any block can be read using the SignalReader instance
of the SignalLoader. That is available using the `reader` property::

    sl = SignalReader(...)
    # get signal not defined in any block
    sig = sl.reader['SIM VFB ALL.DataProcCycle.ObjSyncEgoDynamic.Longitudinal.MotVar.Velocity']
    # get list of all signal names in file
    sig_list = sl.reader.signal_names

Extension
---------

To read single objects (object of interest, ooi) the module `obj_converter` gives an example how to define
the converter and iterator methods.

It is also possible to write an own converter method to return a dictionary using port names
as keys like they defined e.g. for the SignalExtractor. Find a converter using such port names
instead of indices in `obj_converter` module.

:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.9 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/03 07:49:14CEST $
"""
# - STK imports -------------------------------------------------------------------------------------------------------
from stk.io.signalreader import SignalReader

# - defines -----------------------------------------------------------------------------------------------------------
PREFIX = "prefix"
SIGNALS = "signals"
CONV = "conv"
ITER = "iter"
IARGS = "iargs"


# - classes -----------------------------------------------------------------------------------------------------------
class SignalLoader(object):
    """loads signals / objects from given binary file (bsig)

    docu and usage examples see at module description `signal_loader`
    """
    def __init__(self, bsig, **kwargs):  # pylint: disable=W0142
        r"""loader / converter for signals out of a bsig / csv (SignalReader class is used).

        be aware that putting down block size to 4kb inside MTS signal exporter could speed up SignalReader...

        :param bsig: path / to / bsig or csv file
        :type bsig: file or str
        :param kwargs: list of arguments described here, all others are saved to xargs

        :keyword reader: additional options passed to SignalReader init (see example 2)
        :type reader: dict
        :keyword "sig block name": name of signal block giving following parameters to initialise
        :keyword prefix: signal prefix name to be prepended to all signal names
        :type prefix: str
        :keyword signals: list of signal names
        :type signals: list[str]
        :keyword conv: conversation function taking one argument being the signal (numpy array)
        """
        self._args = kwargs.copy()
        self._bsig = SignalReader(bsig, **self._args.pop('reader', {}))

        self._idx = 0
        self._imx = 0
        self._obj_mode = False
        self._idem = None

        for arg, val in self._args.iteritems():
            if CONV not in val:
                val[CONV] = lambda s: s
            # will be called when iterator inits with self, returning if going via block mode and iter amount
            if ITER not in val:
                val[ITER] = {'func': self._dummy_iter, 'args': None}

            pref = val.get(PREFIX, '')
            for sig in val[SIGNALS]:
                if sig['name'].startswith('.'):
                    sig['name'] = pref + sig['name']

    def __enter__(self):
        """with statement usage start"""
        return self

    def _dummy_iter(self, *_):
        """dummy iterator init, used by default to just load single signals
        """
        return False, len(self._idem[SIGNALS])

    def __len__(self):
        """get length of objects / signals

        If a method 'func' is defined in the SignalLoader structure 'iter'
        it will be called here with the defined args.
        So it can be adapted to create special maximum number e.g. for ObjectsOfInterests (OOI)
        or other special signal handling.

        A special conversion method 'conv' is used if the defined 'func' returns True and a max index.
        The method for 'conv' has to be defined also if 'func' returns True!
        """
        try:
            self._obj_mode, self._imx = self._idem[ITER]['func'](self, self._idem[ITER]['args'])
        except TypeError:
            raise
        except:
            self._obj_mode, self._imx = False, 0

        return self._imx

    def __iter__(self):
        """start iterating through signal processing"""
        self._idx = 0
        return self

    def next(self):
        """next item to catch and return

        Stop iteration if maximum index defined in `__len__` is reached,
        there a special method 'func' can be defined e.g. to extract OOI signals.
        """
        if self._idem is None or self._idx >= self._imx:
            raise StopIteration

        obj = self[self._idx]
        self._idx += 1

        return obj

    def __call__(self, item):
        """making a lookalike function call,

        used to take over item of what we want to iterate through actually,
        the iterator for itself is quiet useless as no args can be given.

        ::

          mp = MyProcessor()
          for sig in sigldr('my_signal'):
              mp.proc(sig)
          print(mp.result())

        :param item: named item to iterate over and extract that data
        :returns: self to be able to iterate
        """
        if item not in self._args:
            raise KeyError

        self._idem = self._args[item]
        len(self)
        return self

    @property
    def blockdef(self):
        """return definition of currently used signal block

        this is updated each time a new block is selected,
        after calling ``sl('ars')`` it contains the dictionary
        with the definitions of the 'ars' block: ``{'signals': ....}``
        so it can used in 'conv' and 'iter' methods to e.g. get the defined signals.
        """
        return self._idem

    def __getitem__(self, idx):
        """let's take out that item from bsig as we have it actually...

        :param idx: signal block index to read from SignalReader
        :returns: raw / unconverted signals list
        """
        if idx >= self._imx:
            raise IndexError

        if self._obj_mode:
            return self._idem[CONV](idx, self._idem[SIGNALS])
        else:
            return self._idem[CONV](self._bsig[self._idem[SIGNALS][idx]['name']])

    @property
    def reader(self):
        """
        `SignalReader` instance used here

        can be used to read one signal not defined in any block or call other methods of it
        """
        return self._bsig

    def __contains__(self, item):
        """do we have some item inside us?

        :param item: the one to check
        """
        return item in self._args

    def __exit__(self, *_):
        """close down file (with support)"""
        self.close()

    def __del__(self):
        """in case someone forgot to call close"""
        self.close()

    def close(self):
        """close sig reader"""
        if self._bsig is not None:
            self._bsig.close()
            self._bsig = None


class ObjSignals(object):
    """
    class providing methods to read complete object signals for the SignalLoader

    The needed methods `xinit` to initiate the iterator and the converter method `get_sig`
    can be used in the SignalLoader initialisation to define a block of object signals to be read::

        obj_sigs = ObjSignals()
        with SignalLoader(join(DATAPATH, "Continuous_2014.05.06_at_11.14.13.bsig"),
                          obj={'prefix': 'SIM VFB ALL.DataProcCycle.EmGenObjectList',
                               'signals': [{'name': '.aObject[%].General.uiLifeCycles'},
                                           {'name': '.aObject[%].Kinematic.fDistX'},
                                           {'name': '.aObject[%].Kinematic.fDistY'}],
                               'conv': obj_sigs.get_sig,
                               'iter': {'func': obj_sigs.xinit,
                                        'args': self}}) as sl:

    To mark the object index the '%' character is used similar to the most commonly used definition
    in signal lists of the SignalExtractor.

    This definition will return a list like structure with the defined signals
    that can easily be passed through in loops::

            for sig in sl('obj'):
                for idx in sig[0]:
                    dist = sig[1][idx] ** 2 + sig[2][idx] ** 2
                    ...

    """
    def __init__(self):
        self._loader = None

    def xinit(self, loader, *_):
        """ get number of objects with given name

        here: split first object signal name at '%' and count signal names containing front and end of it

        :param loader: SignalLoader instance
        :param args: provided arguments from signal loader, not used here
        :return: True (as it is a valid conv class method), number of objects
        """
        self._loader = loader
        siglist = loader.reader.signal_names
        sigmask = loader.blockdef['signals'][0]['name'].split('%')
        return True, len([s for s in siglist if sigmask[0] in s and sigmask[1] in s])

    def get_sig(self, idx, _):
        """
        get one signal block with complete object signals

        :param idx: global index of object
        :param signals: list of dict with signal names to process, not used here
        :return: list of signals
        :rtype: list of narrays
        """
        obj = []
        for sig in self._loader.blockdef['signals']:
            try:
                obj.append(self._loader.reader[sig['name'].replace('%', str(idx))])
            except:
                break  # last index reached
        return obj

"""
CHANGE LOG:
-----------
$Log: signal_loader.py  $
Revision 1.9 2017/07/03 07:49:14CEST Mertens, Sven (uidv7805) 
make a copy b4 changing
Revision 1.8 2016/11/29 12:04:44CET Hospes, Gerd-Joachim (uidv8815) 
update docu
Revision 1.7 2016/10/27 12:15:46CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
Revision 1.6 2016/10/27 11:24:52CEST Hospes, Gerd-Joachim (uidv8815)
finetuning and further docu
Revision 1.5 2016/10/25 12:20:08CEST Hospes, Gerd-Joachim (uidv8815)
add ObjSignals class with tests and docu
Revision 1.4 2016/10/21 11:44:12CEST Hospes, Gerd-Joachim (uidv8815)
update, fix docu, rem. port declaration also in test as not needed here
Revision 1.3 2016/03/31 16:36:29CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.2 2015/06/30 11:10:13CEST Mertens, Sven (uidv7805)
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:10:13 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.1 2015/06/26 09:40:14CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/io/project.pj
"""
