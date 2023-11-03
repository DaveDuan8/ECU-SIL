"""
framework/util/logger
---------------

Logger class for logging messages to the console and/or file

**User-API Interfaces**

    - `utils` (complete package),
    - `Logger`,
    - `LoggerException`

Other defined classes for internal usage, interface changes are possible without warning.

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:22:58CEST $
"""


# - imports -----------------------------------------------------------------------------------------------------------
import sys
from collections import OrderedDict
from logging import NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, getLogger, addLevelName, \
    FileHandler, StreamHandler, Formatter
from os import getpid, environ

# - framework imports -------------------------------------------------------------------------------------------------------
from framework.util.error import StkError
from framework.util.helper import singleton

_all__ = ["Logger", "LoggerException"]

# - defines -----------------------------------------------------------------------------------------------------------
EXCEPTION = CRITICAL + 10

LEVEL_CALL_MAP = OrderedDict((('notset', 0), ('debug', DEBUG), ('info', INFO), ('warning', WARNING),
                              ('error', ERROR), ('critical', CRITICAL), ('exception', EXCEPTION)))

MEM_LEVELS = ((1228, DEBUG), (1433, INFO), (1638, WARNING), (sys.maxsize, CRITICAL))
MBYTE = 1048576


# - classes -----------------------------------------------------------------------------------------------------------
class LoggerException(StkError):
    """Database errors """
    def __init__(self, description):
        self.__description = description
        StkError.__init__(self, description)

    def __str__(self):
        return str(self.__description)


@singleton
class LoggerManager(object):
    """
    **the singleton logging mechanism **

    for handling runtime information of different modules.

    If no output stream is defined 'sys.stdout' is used.
    """

    DEBUG, INFO, WARNING, ERROR, CRITICAL = range(10, 51, 10)

    # def __init__(self, logger_name, level=DEBUG, filename=None, strm=None):

    def __init__(self, filename=None, strm=None):
        """init the real logger (but just once)"""
        self._statistics = {v: 0 for v in LEVEL_CALL_MAP.values()}
        self._level = NOTSET
        self._lastmsg = None
        self.handlers = []
        self._pid = getpid()

        if not strm:
            strm = sys.stdout

        # we're on HPC cluster, here we're using appstarter log and want to prevent double timing prints...
        self._use_print = "CCP_SCHEDULER" in environ and strm in [sys.stdout, sys.stderr]

        addLevelName(EXCEPTION, 'EXCEPTION')
        logger = getLogger()

        # log handlers are not cleaned up, but left behind,
        # so we initialize every time anew, but doesn't matter, as for each logger needed,
        # we're not calling get_logger frequently
        while len(logger.handlers) > 0:
            print("remove logger handler: {}".format(logger.handlers[0]))
            logger.removeHandler(logger.handlers[0])

        logger.setLevel(DEBUG)

        if filename is not None:
            try:
                handler = FileHandler(filename, "w")
            except:
                raise LoggerException("Couldn't create/open file '%s'. Please check permisions." % filename)

            formatter = Formatter("%(asctime)s %(name)-15s - %(levelname)s: %(message)s", "%d.%m.%Y %H:%M:%S")
            handler.setFormatter(formatter)
            handler.setLevel(DEBUG)
            self.handlers.append(handler)

        if not self._use_print:
            handler = StreamHandler(strm)
            formatter = Formatter("%(asctime)s %(name)s - %(levelname)s: %(message)s", "%d.%m.%Y %H:%M:%S")
            handler.setFormatter(formatter)
            handler.setLevel(DEBUG)
            self.handlers.append(handler)

        for i in self.handlers:
            logger.addHandler(i)

    @property
    def level(self):
        """retrieves initial debug level
        """
        return self._level

    @level.setter
    def level(self, level):
        """sets initial debug level

        :param level: this level will be taken once when not set before
        :return: level
        """
        if self._level == NOTSET:
            if level == NOTSET:
                self._level = DEBUG
            else:
                self._level = level

    def get_statistics(self):
        """Gets number of each type of logging message"""
        return OrderedDict((k, self._statistics[v]) for k, v in LEVEL_CALL_MAP.items())

    @property
    def lastmsg(self):
        """returns the last logging message text"""
        return self._lastmsg

    def log(self, name, baselevel, level, msg):
        """do the log

        :param name: name of logger to use
        :param baselevel: base log level of logger
        :param level: level of logging
        :param msg: message to log
        """
        if level >= baselevel:
            if self._use_print:
                if level > INFO:
                    sys.stderr.write(msg + '\n')
                else:
                    print(msg)
            if len(self.handlers) > 0:
                getLogger(name).log(level, msg)
                # log handlers are not cleaned up, but left behind,
                # so we initialize every time anew, but doesn't matter, as for each logger needed,
                # we're not calling get_logger frequently
                # while len(logger.handlers) > 0:
                #     print("remove logger handler: {}".format(logger.handlers[0]))
                #     logger.removeHandler(logger.handlers[0])

            self._statistics[level] += 1
        else:
            self._statistics[0] += 1

        self._lastmsg = msg


class ProxyLogger(object):
    """Wrapper object for a method to be called.
    """
    def __init__(self, func, **xargs):
        """
        :param func: function / method to wrap
        :param xargs: arguments to pass via __call__
        """
        self.func, self.xargs = func, xargs

    def __call__(self, *args, **kwds):
        """
        :param args: additional arguments
        :param kwds: even more arguments to pass than given in __init__
        :return: result from actual function call
        """
        self.xargs.update(kwds)
        # pylint: disable=protected-access
        if len(args) == 1:  # can only be the msg
            self.xargs.update({'msg': args[0]})
            return self.func(**self.xargs)
        elif len(args) == 0 and 'level' in self.xargs and self.xargs['level'] == DEBUG:
            # pylint: disable=protected-access
            # noinspection PyProtectedMember
            self.xargs['msg'] = str(sys._getframe(1).f_code.co_name) + "()" + " called."
            return self.func(**self.xargs)
        else:
            return self.func(*args, **self.xargs)


class Logger(object):
    """logger instance

    :

    usage

    .. code-block:: python

        from logging import DEBUG
        # logging to file + console
        main_logger = logger.Logger("my_main_logger", level=DEBUG, filename="my_logging_file.log")

        # logging to console
        main_logger = logger.Logger("my_main_logger", level=DEBUG)

        #where:
        #  logger_name: is the name of the logger
        #  level:       is the logging level [10=DEBUG, 20=INFO,
        #                                     30=WARNING, 40=ERROR,
        #                                     50=CRITICAL]
        #  filename:    None : only console,  FilePath: Log file

        # displays message as debug
        main_logger.debug("This is a debug message")
        # displays message as info
        main_logger.info("This is an info message")
        # displays message as warning
        main_logger.warning("This is a warning")
        # displays message as error
        main_logger.error("This is an error message")
        # displays message as critical
        main_logger.critical("This is a critical message")
        # displays message as exception
        # -> to be called from an exception handler
        main_logger.exception("This is an exception message")

        # change global logging level to INFO level (from logging import INFO)
        main_logger.level = INFO

        # log memory usage info of current process < 1.2GB, level will be DEBUG, etc...
        main_logger.mem_usage()

        # retrieve actual logging level
        lev = main_logger.level

        # retrieve statistics
        stats = main_logger.get_statistics()

        # created from another script
        logger2 = logger.Logger("my_logger2")
        # displays message as info
        logger2.info(" This is an info message")
        #...

    """
    def __init__(self, logger_name, level=NOTSET, filename=None, strm=None):
        """your logger...

        :param logger_name: name of global logger
        :type logger_name: str
        :param level: initial level of logging, if NOTSET, DEBUG level will be used
        :type level: int
        :param filename: name of file (incl. path) to log to
        :type filename: str | None
        :param strm: stream to push logs out as well
        :type strm: None | stdout | stderr
        """
        self._logger_name = logger_name
        self._logger = LoggerManager(filename, strm)
        self._logger.level = level
        if level == NOTSET:
            self._level = self._logger.level
        else:
            self._level = level

    def __getattr__(self, item):
        """uses proxy to pass calls to logger manager

        :param item: log level
        :type item: str
        :return: function pointer from logger manager to debug, info, etc method
        """
        if item in LEVEL_CALL_MAP:
            return ProxyLogger(self._logger.log, name=self._logger_name,
                               baselevel=self._level, level=LEVEL_CALL_MAP[item])
        elif hasattr(self._logger, item):
            return getattr(self._logger, item)
        else:
            raise AttributeError(item)

    @property
    def level(self):
        """returns current log level"""
        return self._level

    @level.setter
    def level(self, level):
        """changes level of logger

        :param level: level to change global level to
        """
        self._level = level

    def log(self, level, msg):
        """log a msg at a certain level

        :param msg: message to log
        :param level: level to use
        """
        self._logger.log(self._logger_name, self._level, level, msg)

    if 0:  # please, don't remove: kept here for documentation purposes and intellisense...
        @staticmethod
        def debug(msg=None):
            """do a debug log entry

            :param msg: message to push to logger, can be left out to just state your method has been called.
            """
            pass

        @staticmethod
        def info(msg):
            """do an info log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def warning(msg):
            """do a warning log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def critical(msg):
            """do a critical log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def error(msg):
            """do an error log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def exception(msg):
            """do an exception log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def mem_usage():
            """does a log at certain level of how much memory is in use and peak mem was used
            """
            pass

        @staticmethod
        def get_statistics():
            """returns statistics

            :returns: statistics of how much messages have been sent via levels
            """
            pass


"""
CHANGE LOG:
-----------
$Log: logger.py  $
Revision 1.2 2020/03/31 09:22:58CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:25CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
