"""
framework.error.py
------------

This Module contains the General Exception Handling Methods, which are available inside the framework.

:org:           Continental AG
"""

# Import Python Modules -----------------------------------------------------------------------------------------------
# noinspection PyProtectedMember
from sys import _getframe
from os import path as opath

# Defines -------------------------------------------------------------------------------------------------------------
ERR_OK = 0
"""Code for No Error"""
ERR_UNSPECIFIED = 1
"""Code for an unknown Error"""

# Classes -------------------------------------------------------------------------------------------------------------


class StkError(Exception):
    """
    **Base STK exception class**,

    where all other Exceptions from the stk sub-packages must be derived from.
    
    Frame number is set to 2 thereof.

    - Code for No Error: ERR_OK
    - Code for an unknown / unspecified Error: ERR_UNSPECIFIED
    """

    ERR_OK = ERR_OK
    """Code for No Error"""
    ERR_UNSPECIFIED = ERR_UNSPECIFIED
    """Code for an unknown Error"""

    def __init__(self, msg, errno=ERR_UNSPECIFIED, dpth=2):
        """
        retrieve some additional information

        :param msg:   message to announce
        :type msg:    str
        :param errno: related error number
        :type errno:  int
        :param dpth:  starting frame depth for error trace, increase by 1 for each subclass level of StkError
        :type dpth:   int
        """
        Exception.__init__(self, msg)
        frame = _getframe(dpth)
        self._errno = errno
        self._error = "'%s' (%d): %s (line %d) attr: %s" \
                      % (msg, errno, opath.basename(frame.f_code.co_filename), frame.f_lineno, frame.f_code.co_name)

    def __str__(self):
        """
        :return: our own string representation
        :rtype: str
        """
        return self._error

    @property
    def error(self):
        """
        :return: error number of exception
        :rtype: int
        """
        return self._errno


class ValfError(StkError):
    """
    Exception Class for all Valf Exceptions.

    :author:        Joachim Hospes
    :date:          26.09.2013
    """
    ERR_OBSERVER_CLASS_NOT_FOUND = 101
    """Observer Class Name not found."""

    def __init__(self, msg, errno=StkError.ERR_UNSPECIFIED, dpth=2):
        """
        Init Method of Exception class

        :param msg:   Error Message string, which explains the user was went wrong.
        :type msg:    string
        :param errno: unique number which represents a Error Code inside the Package.
        :type errno:  integer
        :param dpth:  depth of call stack to start error frame output, StkError is level 1, fist subclass level 2...

        :author:      Joachim Hospes
        :date:        26.09.2013
        """
        StkError.__init__(self, msg, errno=errno, dpth=dpth)

"""
CHANGE LOG:
-----------
$Log: error.py  $
Revision 1.2 2020/03/31 09:22:56CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:24CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
