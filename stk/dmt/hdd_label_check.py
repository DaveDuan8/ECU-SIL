"""
hdd_label_check.py
------------------

**method `hdd_label_check` to check if label of connected HDD follows the naming convention**

as additional option the module can be called as script to be used in batch files

**user api:**

    - `hdd_label_check`     check passed label name
    - `hdd_drive_check`     check label of connected drive

**HDD volume naming convention**::

    format:  DMTxxxxxx
        DMT:          short for "Data Management" (3digits)
        xxxxxx:       DMT internal consecutive number (6 digits)

example: ``DMT009000``

Definitions:

DMT internal consecutive number sequence: 009000 - 009999.

Volume name shall be like the defined format and consecutive sequence number.

=> DMT009000 - DMT009999


**call options:**

usage: hdd_label_check.py [-h] [-e] name

-h      print help
-e      exit on failed check
name    drive name ( c:\\ ) or label name to check

exit value: 0 if name ok, -1 else

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/09/29 17:02:15CEST $
"""

# - imports -----------------------------------------------------------------------------------------------------------
from win32api import GetVolumeInformation, error as win_error
from re import compile as recompile
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from sys import exit as sexit

# - defines -----------------------------------------------------------------------------------------------------------
HDD_NAME_REGX = r'^DMT\d{6,6}$'
HDD_NAME_MATCH = recompile(HDD_NAME_REGX)


# - functions ---------------------------------------------------------------------------------------------------------
def hdd_label_check(name, raise_exception=False):
    """
    check if hdd label is following naming convention (see module docu above)

    with raise_exception set to True it raises a ValueError if name does not match

    :param name: label name to check
    :type  name: str
    :param raise_exception: set to True if a ValueError should be thrown in case of missing the convention
    :type  raise_exception: bool
    :return: check result: True if naming convention is confirmed
    :rtype:  bool
    """
    match = HDD_NAME_MATCH.match(name)
    if raise_exception and not match:
        raise ValueError('HDD label "%s" does not follow naming convention')
    return True if match else False


def hdd_drive_check(drive, raise_exception=False):
    """
    check if label of passed drive name is following naming convention (see module docu above)

    :param drive: Windows drive name (like 'c:\\')
    :type  drive: str
    :param raise_exception: set to True if a ValueError should be thrown in case of missing the convention
    :type  raise_exception: bool
    :return: check result: True if naming convention is confirmed
    :rtype:  bool
    """
    try:
        name = GetVolumeInformation(drive)[0]
    except win_error:
        name = "NoDriveAvailable"
    return hdd_label_check(name, raise_exception=raise_exception)


def main():
    """
    call options for hdd_label_check:

    usage: hdd_label_check.py [-h] [-e] name

    -h      print help
    -e      exit on failed check
    name    drive name ( c:\\ ) or label name to check

    exit level: 0 if check ok, -1 otherwise
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument(dest="name", type=str, help="hdd label to check")
    opts.add_argument("-e", dest="raise_exception", action='store_true', default=False, help="exit on failed check")
    args = opts.parse_args()

    if args.name.find(':') > 0:
        return int(hdd_drive_check(args.name, args.raise_exception)) - 1

    return int(hdd_label_check(args.name, args.raise_exception)) - 1


if __name__ == '__main__':
    sexit(main())

"""
CHANGE LOG:
-----------
$Log: hdd_label_check.py  $
Revision 1.2 2015/09/29 17:02:15CEST Hospes, Gerd-Joachim (uidv8815) 
fix pep8, pylint errors
- Added comments -  uidv8815 [Sep 29, 2015 5:02:16 PM CEST]
Change Package : 376234:1 http://mks-psad:7002/im/viewissue?selection=376234
Revision 1.1 2015/09/29 16:46:03CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/dmt/project.pj
"""
