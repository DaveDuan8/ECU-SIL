"""
__init__.py
-----------

sub-package to handle tooling around MTS.
"""
__all__ = []

from six import PY2

# - defines ------------------------------------------------------------------------------------------------------------
if PY2:
    from types import StringTypes
    BSIG_HDR, BSIG_FTR = ('B', 'S', 'I', 'G'), ('B', 'I', 'N', '\x00')
else:
    BSIG_HDR, BSIG_FTR = (b'B', b'S', b'I', b'G'), (b'B', b'I', b'N', b'\x00')
    StringTypes = (str,)

SIG_NAME = 'SignalName'
SIG_TYPE = 'SignalType'
SIG_ARRAYLEN = 'ArrayLength'
SIG_OFFSET = 'Offsets'
SIG_SAMPLES = 'SampleCount'
