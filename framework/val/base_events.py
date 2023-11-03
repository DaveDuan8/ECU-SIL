"""
Observer Template
-----------------

base event classes for result db events

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:34:06CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from UserList import UserList
from copy import copy
from inspect import currentframe
from os import path


from ..util.helper import list_folders
from ..util.logger import Logger
from .asmt import ValAssessment

# - defines -----------------------------------------------------------------------------------------------------------
HEAD_DIR = path.abspath(path.join(path.dirname(currentframe().f_code.co_filename), ".."))

PLUGIN_FOLDER_LIST = []
for folder_path in list_folders(HEAD_DIR):
    PLUGIN_FOLDER_LIST.append(folder_path)


# - classes -----------------------------------------------------------------------------------------------------------
# =====================================================================================================================
# Exceptions
# =====================================================================================================================
class ValEventError(StandardError):
    """Base of all Event errors"""
    def __init__(self, msg):
        """

        :param msg: Exception message
        :type msg: Stromg
        """
        StandardError.__init__(self, msg)


class ValBaseEventAttributes(object):
    """
    Base Class for the validation attributes
    """
    def __init__(self, value=0, unit='', value_type='float', image=None):
        """Base Event Attribute Init
        """
        self.__value = value
        self.__unit = unit
        self.__valueType = value_type
        self.__image = image

    def __del__(self):
        """clean up
        """
        # print 'Event destroyed'
        self.__value = 0
        self.__unit = ''
        self.__valueType = ''

    def __copy__(self):
        cp = ValBaseEventAttributes(self.get_value(), self.get_unit(), self.get_type(), self.get_image())

        return cp

    def set_value(self, value, value_type=None):
        """ Set the value and value type
        """
        if value_type is not None:
            self.__valueType = value_type
        self.__value = value

    def get_value(self):
        """ Returns the value
        """
        return self.__value

    def get_unit(self):
        """ Returns the unit
        """
        return self.__unit

    def get_type(self):
        """ Returns the value type
        """
        return self.__valueType

    def get_image(self):
        """ Returns the image
        """
        return self.__image

    def __str__(self):
        me = "value : %s, Unit %s, ValueType %s" % (str(self.__value), self.__unit, self.__valueType)
        return me


class ValBaseEventDetails(object):
    """
    Base Class for the validation event details
    """
    def __init__(self, rel_timestamp=-1):
        """initializer taking the rel_timestamp

        @param rel_timestamp: relative timestamp
        """
        self.__timestamp = rel_timestamp
        self.__attributes = {}

    def __del__(self):
        """
        last cleanup
        """
        # print 'Event destroyed'
        self.__timestamp = 0
        del self.__attributes

    def __copy__(self):
        cp = ValBaseEventDetails(self.get_timestamp())

        cp.__attributes = copy(self.__attributes)

        return cp

    def get_timestamp(self):
        """ Return relative timestamp """
        return self.__timestamp

    def add_attribute(self, attribute_name, value=0, unit='', value_type='float', image=None):
        """ Add a Attribute to the event detail """
        if image is not None:
            if not isinstance(image, buffer):
                raise ValEventError("Adding attribute fail. Image for Attribute %s at timestamp %s is not a buffer." %
                                    (attribute_name, str(self.__timestamp)))

        if self.__timestamp == -1:
            self.__add_attribute(attribute_name, value, unit, value_type, image)
        else:
            if attribute_name not in self.__attributes:
                self.__add_attribute(attribute_name, value, unit, value_type, image)
            else:
                raise ValEventError("Adding attribute fail.Attribute %s for timestamp %s already exist." %
                                    (attribute_name, str(self.__timestamp)))

    def __add_attribute(self, attribute_name, value, unit, value_type, image):
        """ Add a Attribute to the event detail """
        attribute = ValBaseEventAttributes(value=value, unit=unit, value_type=value_type, image=image)
        self.__attributes.setdefault(attribute_name.lower(), []).append(attribute)

    def update_attribute(self, attribute_name, value):
        """ Update the Attribute of the event detail """
        name = attribute_name.lower()
        if attribute_name in self.__attributes:
            self.__attributes[name][0].set_value(value)
        else:
            raise ValEventError("Attribute " + attribute_name + " does not exist. Update of value not possible")

    def get_attribute_names(self):
        """ Return names of all the attributes """
        return self.__attributes.keys()

    def get_attribute(self, name):
        """ Return attribute objekt """
        name = name.lower()
        if name in self.__attributes:
            return self.__attributes[name]
        else:
            raise ValEventError("Attribute " + name + " does not exist")

    def get_attribute_value(self, name):
        """ Return attribute value """
        name = name.lower()
        if name in self.__attributes:
            return self.__attributes[name][0].get_value()
        else:
            raise ValEventError("Attribute " + name + " does not exist. Failed to get value")

    def get_attribute_values(self, name):
        """ Return attribute values """
        name = name.lower()
        if name in self.__attributes:
            values = []
            for attribute in self.__attributes[name]:
                values.append(attribute.get_value())
            return values
        else:
            raise ValEventError("Attribute " + name + "  does not exist. Failed to get values of it")

    def get_attribute_image(self, name):
        """ Return attribute image """
        name = name.lower()
        if name in self.__attributes:
            return self.__attributes[name][0].get_image()
        else:
            return None

    def get_attribute_type(self, name):
        """ Return attribute type """
        name = name.lower()
        if name in self.__attributes:
            return self.__attributes[name][0].get_type()
        else:
            raise ValEventError("Attribute " + name + " does not exist. Failed to get attribute type info")

    def get_attribute_unit(self, name):
        """ Return attribute unit """
        name = name.lower()
        if name in self.__attributes:
            return self.__attributes[name][0].get_unit()
        else:
            raise ValEventError("Attribute " + name + " does not exist. Failed to get unit info")

    def delete_attribute(self, name):
        """ Delete  attribute values """
        name = name.lower()
        if name in self.__attributes:
            self.__attributes.pop(name)
        else:
            raise ValEventError("Attribute " + name + " does not exist. Failed to deleted attribute")

    def __str__(self):
        me = ("Timestamp : %d\n" % self.__timestamp)
        for items in self.__attributes:
            for idx in xrange(len(self.__attributes[items])):
                me += ("%s : %s\n" % (items, self.__attributes[items][idx].get_value()))
        return me


class ValBaseEventDetailsContainer(UserList):
    """
    Base Class of the validation event details container
    """
    def __init__(self, timestamps=None):
        """Initializer taking the timestamps

        @param timestamps: absolute timestamps
        """
        UserList.__init__(self)
        self.__logger = Logger(self.__class__.__name__)

        self.__event_details_map = {}

        self.set_timestamps(timestamps)

    def __del__(self):
        """last cleanup
        """
        del self.__event_details_map

    def __copy__(self):
        """TODO
        """
        cp = ValBaseEventDetailsContainer(self.get_time_stamps())

        cp.__event_details_map = copy(self.__event_details_map)
        cp.data = copy(self.data)

        return cp

    def get_time_stamps(self):
        """ Returns the array of timestamps of the Event
        """
        if len(self.data) > 0:
            return sorted(self.__event_details_map.keys())

    def set_timestamps(self, timestamps):
        """ if the timestamps are valid create event details for all the timestamps """
        if timestamps is not None:
            for timestamp in timestamps:
                if timestamp not in self.__event_details_map:
                    event_details = ValBaseEventDetails(timestamp)
                    self.data.append(event_details)
                    self.__event_details_map[timestamp] = self.data.index(event_details)

    def add_timing_attribute(self, attribute_name, value=None, unit='', value_type='float', image=None):
        """ Add a Attribute to all event details """
        if value is None:
            value = []
        length = len(value)
        for item in self.data:
            if length > 0:
                try:
                    index = self.data.index(item)
                    item.add_attribute(attribute_name, value=value[index], unit=unit, value_type=value_type,
                                       image=image)
                except ValEventError, ex:
                    self.__logger.error(str(ex))
            else:
                # add default attribute
                item.add_attribute(attribute_name)

    def update_timing_attribute(self, attribute_name, value):
        """ Update all Attribute of the event details """
        if len(value) == len(self.data):
            try:
                for item in self.data:
                    index = self.data.index(item)
                    item.update_attribute(attribute_name, value=value[index])
            except ValEventError, ex:
                self.__logger.error(str(ex))
        else:
            self.__logger.error("Input vector has different size, input: %d != int %d" % (len(self.data), len(value)))

    def get_timing_attribute_names(self):
        """ Return names of all the attributes """
        if len(self.data) > 0:
            return self.data[0].get_attribute_names()
        else:
            return {}

    def get_timing_attribute_values(self, name):
        """ Return attribute values """
        values = []
        try:
            for item in self.data:
                values.append(item.get_attribute_value(name))
        except ValEventError, ex:
            self.__logger.info(ex)

        return values

    def get_timing_attribute_units(self, name):
        """ Return attribute units """
        units = []
        for item in self.data:
            units.append(item.get_attribute_unit(name))
        return units

    def get_timing_attribute_images(self, name):
        """ Return attribute images """
        images = []
        for item in self.data:
            images.append(item.get_attribute_image(name))
        return images

    def __str__(self):
        lines = ["Timestamps  : "]
        if self.get_time_stamps() is not None:
            lines[0] += ','.join([str(i) for i in self.get_time_stamps()])
            attr_names = self.get_timing_attribute_names()
            for name in attr_names:
                lines.append("%s : " % name)

            for name in attr_names:
                attr_index = attr_names.index(name) + 1
                values = self.get_timing_attribute_values(name)
                lines[attr_index] += str(values).strip('[]')

            string = ""
            for line in lines:
                string += "%s\n" % line
        else:
            string = "no timing attributes"
        return string


class ValBaseSingleton(object):
    """ Singleton Class for storing instance which should be only once created """
    __instances = []

    @staticmethod
    def __del__():
        """ Destructor """
        for instance in ValBaseSingleton.__instances:
            instance.__del__()


class ValEventDatabaseInterface(object):
    """ Event Database Interface class """
    def __init__(self, db_connection):
        self.__db_connections = db_connection
        self._ValResDB = None
        self._GblDB = None
        self._GenLblDB = None
        self._RecCatDB = None
        self._ObjDataDB = None
#
        # self.__InitializeDBConnection(self.__db_connections)

        self.__userid = None
        self.__wfid = None
        self.__assessment = {}
        self.__observer_types = {}
        self.__event_types_ids = {}

    def __del__(self):
        self.__db_connections = None
        self._ValResDB = None
        self._GblDB = None
        self._GenLblDB = None
        self._RecCatDB = None
        self._ObjDataDB = None

        self.__event_types_ids = {}


class ValEventSaver(ValEventDatabaseInterface):
    """ ValEventSaver Save event in the database """
    def __init__(self, db):
        """
        Constructor taking database connection

        @param db: Database Connection Dict
        """
        ValEventDatabaseInterface.__init__(self, db)
        self.__unit_ids = {}
        self.__attribute_types_ids = {}

    def __del__(self):
        """ Destructor """

        self.__unit_ids = {}
        self.__attribute_types_ids = {}


class ValBaseEvent(ValBaseEventDetailsContainer, ValBaseEventDetails):
    """
    Base Class for the validation event
    """
    def __init__(self, start_time=0, start_index=-1, stop_time=0, stop_index=-1,
                 timestamps=None, seid=None, assessment_id=None, measid=None):
        """
        Constructor taking the starttime, startindex and the eventtype as argument

        :param start_time: Absolute Time Start
        :param start_index: Start index
        :param stop_time: Stop time of the event
        :param stop_index: Stop index of the event
        :param timestamps: Timestamps vector (optional)
        :param seid: DB unique identifier (when loading)
        :param assessment_id: Assessment identifier of the event (downward compatibility)
        :param measid: measid of the event (measurement)
        """
        self.__logger = Logger(self.__class__.__name__)

        self.__assid = assessment_id
        self.__seid = seid
        self.__measid = measid
        self.__rdid = None
        self.__parent = None
        self.__assessment = None

        ValBaseEventDetailsContainer.__init__(self, timestamps)
        # create the global event attributes object, for attibutes with not time informations
        ValBaseEventDetails.__init__(self)

        self.__type = self.__class__.__name__
        self.__ref_tag = None
        self.__start_time = start_time
        self.__start_index = start_index
        self.__stop_time = stop_time  # Event Stop Time
        self.__stop_index = stop_index  # Event Stop Index

    def __del__(self):
        """
        Destructor
        """
        self.__assid = None
        self.__seid = None
        self.__type = None

    def __copy__(self):
        cp = ValBaseEvent()
        cp.__dict__ = copy(self.__dict__)

        return cp

    # def GetDurationMicroSeconds(self):
    #     """ Return the timespan of the event
    #
    #     :return Duration in micro seconds
    #     """
    #     if self.__start_time <= self.__stop_time:
    #         return self.__stop_time - self.__start_time
    #     raise ValEventError("Event not finished")

    def get_event_cycles(self):
        """ Return the timespan of the event

        :return Duration in cycles
        """

        if self.__start_index + 1 <= self.__stop_index + 1:
            return self.__stop_index - self.__start_index + 1
        raise ValEventError("Event not finished")

    def set_type(self, value):
        """ Set the Type of the Object
        """
        self.__type = value

    def add_assessment(self, assessment):
        """ Add Assessment Instance to the result

        :param assessment: Assessment instance
        :return: True if passed, False on Error
        """
        if not issubclass(assessment.__class__, ValAssessment):
            self.__logger.error("Not an Assessment Class Instance")
            return False

        self.__assessment = assessment
        self.__assid = self.__assessment.ass_id
        return True

    def get_assessment(self):
        """ Returns event assessment """
        return self.__assessment

    def get_start_time(self):
        """ Returns the Start-time of the Event
        """
        return self.__start_time

    def get_stop_time(self):
        """ Returns the Stop-time of the Event
        """
        return self.__stop_time

    def get_start_index(self):
        """ Returns the StopIndex of the Event
        """
        return self.__start_index

    def get_stop_index(self):
        """ Returns the StopIndex of the Event
        """
        return self.__stop_index

    def get_meas_id(self):
        """ Get the measurement identifier of the event """
        return self.__measid

    def get_rd_id(self):
        """ Get the result descriptor Identifier of the event """
        return self.__rdid

    def __str__(self):
        me = ""
        if self.__type is not None:
            me += ("Event Type  : %s\n" % self.__type)
        if self.__start_index is not None:
            me += ("Start index : %d\n" % self.__start_index)
        if self.__stop_index is not None:
            me += ("Stop index  : %d\n" % self.__stop_index)
        if self.__start_time is not None:
            me += ("Start time  : %d\n" % self.__start_time)
        if self.__stop_time is not None:
            me += ("Stop time   : %d\n" % self.__stop_time)
        if self.__seid is not None:
            me += ("Seid ID   : %d\n" % self.__seid)
        if self.__assessment is not None:
            me += ("Assessment : %s\n" % str(self.__assessment))
        me += "-- Global event attributes ---\n"
        me += ValBaseEventDetails.__str__(self)
        me += "-- Timing event attributes ---\n"
        me += ValBaseEventDetailsContainer.__str__(self)

        return me


"""
    CHANGE LOG:
-----------
$Log: base_events.py  $
Revision 1.1 2020/03/25 21:34:06CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
