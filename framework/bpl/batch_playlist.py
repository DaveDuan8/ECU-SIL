"""
batch_playlist.py
-----------------
Handles reading contents of batch playlists.
"""

import os
import logging
import xml.etree.ElementTree as ElementTree

__author__ = "Leidenberger, Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 20:58:03CET $"

_log = logging.getLogger("BatchPlayList")


class BatchPlaylist(object):
    def __init__(self, filename):
        super(BatchPlaylist, self).__init__()

        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()

    @property
    def recordings(self):
        """
        A list of all entries
        :return:
        """
        recordings = []
        for be in self.root.iter('BatchEntry'):
            _log.debug(be.attrib["fileName"])
            recordings.append(be.attrib["fileName"])
        return recordings

    @classmethod
    def create_from_directory(cls, dirs=''):
        if hasattr(dirs, '__iter__'):
            for dir_ in dirs:
                if os.path.exists(dir_) and os.path.isdir(dir_):
                    pass
