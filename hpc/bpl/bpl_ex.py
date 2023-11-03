# -*- coding: iso-8859-1 -*-
"""
bpl_ex.py
---------

Classes for BPL (BatchPlayList) Handling, supports BPL (of course), collection, ini and text files
"""


# - classes ------------------------------------------------------------------------------------------------------------
class BplException(Exception):
    """
    used by Bpl class to indicate file handling problems

    **errno:**

        - 1: file format wrong
        - 2: file cannot be opened
    """

    def __init__(self, msg):
        """overwrite"""
        Exception.__init__(self, msg)
