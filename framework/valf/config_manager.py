"""
framework.valf.config_manager.py
------------------------------
:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:10CEST $
"""

# - import Python modules ---------------------------------------------------------------------------------------------
import configparser

# - import framework modules ------------------------------------------------------------------------------------------------
import framework.util.logger as log


# - classes -----------------------------------------------------------------------------------------------------------
class ConfigManager(object):
    """ main valf part to manage configuration """
    def __init__(self, data_manager, plugin_manager):
        """TODO
        """
        self.__logger = log.Logger(self.__class__.__name__)
        self.__data_manager = data_manager
        self.__plugin_manager = plugin_manager

        self.__object_map_list = []
        self.__object_map = {}
        self.__ini_reader = None

    # def _get_port_names(self, component_name):
    #     """
    #     component_ports = None
    #
    #     try:
    #         component_ports = self.__ini_reader.GetSectionKeys(component_name)
    #     except Exception as ex:
    #         self.__logger.exception(str(ex))
    #
    #     if component_ports:
    #         return component_ports
    #
    #     return None

    def _read(self, config_file_path):  # pylint: disable=R0912,R0914,R0915
        """TODO
        """
        config = configparser.RawConfigParser()
        try:
            config.read(config_file_path)
        except Exception as ex:
            self.__logger.exception(str(ex))
            self.__logger.error("Couldn't read config file '%s' due to previous exception." % config_file_path)
            return None

        # component_name_list = []
        component_name_list = config.sections()
        if not len(component_name_list):
            self.__logger.error("Invalid configuration file: '%s'" % config_file_path)
            return None

        # component_list = []
        component_map = {}
        try:
            for component_name in component_name_list:
                # noinspection PyBroadException
                try:
                    active = config.get(component_name, "Active")
                except:
                    active = True

                # when active is False the component will not be loaded
                # noinspection PyBroadException
                try:
                    if str(active).lower() == "false":
                        continue
                except:
                    pass

                # key_name_list = config.options(component_name)

                # noinspection PyBroadException
                try:
                    class_name = config.get(component_name, "ClassName")
                    if len(class_name):
                        class_name = eval(class_name)
                except:
                    class_name = None

                port_out_list = None
                # noinspection PyBroadException
                try:
                    port_out = config.get(component_name, "PortOut")
                    if len(port_out):
                        # noinspection PyBroadException
                        try:
                            port_out_list = eval(port_out)
                        except:
                            tmp = "Invalid port value. "
                            tmp += "[Component: '%s', Port: '%s'.]" % (component_name, "PortOut")
                            self.__logger.error(tmp)
                            return None
                except:
                    port_out_list = []

                input_data_list = None
                # noinspection PyBroadException
                try:
                    input_data = config.get(component_name, "InputData")
                    if len(input_data):
                        # noinspection PyBroadException
                        try:
                            input_data_list = eval(input_data)
                        except:
                            tmp = "Invalid parameter value. [Component: "
                            tmp += "'%s', Parameter: '%s']" % (component_name, "InputData")
                            self.__logger.error(tmp)
                            return None
                except:
                    input_data_list = []

                if class_name:
                    order = config.get(component_name, "Order")
                    if len(order):
                        # noinspection PyBroadException
                        try:
                            order = eval(order)
                        except:
                            tmp = "Invalid parameter value. [Component: "
                            tmp += "'%s', Parameter: '%s']" % (component_name, "Order")
                            self.__logger.error(tmp)
                            return None
                else:
                    order = None

                connect_bus = config.get(component_name, "ConnectBus")
                if len(connect_bus):
                    # noinspection PyBroadException
                    try:
                        connect_bus_list = eval(connect_bus)
                    except:
                        tmp = "Invalid parameter value. [Component: "
                        tmp += "%s, Parameter: %s]" % (component_name, "ConnectBus")
                        self.__logger.error(tmp)
                        return None
                else:
                    self.__logger.error("'ConnectBus' not specified or is invalid.")
                    return None

                component_map[component_name] = {"ClassName": class_name,
                                                 "PortOut": port_out_list,
                                                 "InputData": input_data_list,
                                                 "ConnectBus": connect_bus_list,
                                                 "Order": order}

        except Exception as ex:
            self.__logger.error(str(ex))
            return None

        if len(component_map):
            return component_map

        return None

    @staticmethod
    def _get_component_order(order_list, connection_list):
        max_cnt = 0
        for entry in connection_list:
            max_cnt = max(max_cnt, order_list[entry]["Order"])

        return max_cnt + 1

    def _set_data_port(self, entry):
        """TODO
        """
        component = list(entry.keys())[0]

        # noinspection PyBroadException
        try:
            bus_name = entry[component]["bus"][0]
            if len(bus_name) == 0:
                return None

            for port_name in list(entry[component].keys()):
                if port_name in ["classname", "connectionlist", "bus", "activate"]:
                    continue

                if len(entry[component][port_name]) == 1:
                    self.__data_manager.set_data_port(port_name, entry[component][port_name][0], bus_name)
                else:
                    port_value_list = []
                    for port_value in entry[component][port_name]:
                        idx = port_value.rfind("%")
                        if idx == -1:
                            port_value_list.append(port_value)
                            continue

                        # noinspection PyBroadException
                        try:
                            count = int(port_value[idx + 1: len(port_value)].strip())
                        except:
                            port_value_list.append(port_value)
                            continue

                        port_value = port_value[0:idx].strip()

                        if port_value.find("%d") != -1:
                            for idx in range(count):
                                port_value_list.append(port_value.replace("%d", str(idx)))
                        else:
                            break

                    self.__data_manager.set_data_port(port_name, port_value_list, bus_name)

            return bus_name
        except:
            self.__logger.error("No bus name specified for: '%s'" % component)

        return None

    def load_configuration(self, config_file_path):  # pylint: disable=R0912,R0914
        """TODO
        """
        plugin_map = {}
        self.__logger.info("Searching for plug-ins. Please wait...")
        plugin_class_map_list = self.__plugin_manager.get_plugin_class_list()
        if plugin_class_map_list is None:
            self.__logger.error("No plug-ins found.")
            return None

        self.__logger.info("%d plug-ins found." % len(plugin_class_map_list))
        for plugin_class_map in plugin_class_map_list:
            plugin_map[plugin_class_map['name']] = plugin_class_map["type"]

        component_map = self._read(config_file_path)
        if component_map is None:
            return None

        self.__object_map = {}
        for component_name in list(component_map.keys()):
            class_name = component_map[component_name].get("ClassName")
            # port_in_list = component_map[component_name].get("PortIn")
            port_out_list = component_map[component_name].get("PortOut")
            input_data_list = component_map[component_name].get("InputData")
            connect_bus_list = component_map[component_name].get("ConnectBus")

            if not isinstance(connect_bus_list, list):
                connect_bus_list = [connect_bus_list]

            order = component_map[component_name].get("Order")
            cls_obj = None
            if class_name:
                if class_name in plugin_map:
                    # self.__logger.debug("Loading plug-in: '%s'." % component_name)
                    cls_obj = plugin_map[class_name](self.__data_manager, component_name, connect_bus_list)
                else:
                    self.__logger.error("Invalid component name: '%s'." % class_name)
                    return None

            for port_out in port_out_list:
                for bus_name in connect_bus_list:
                    tmp = "Register port: Provider="
                    tmp += "'%s', PortName='%s', Bus='%s'." % (component_name, port_out, bus_name)
                    self.__logger.debug(tmp)
                    self.__data_manager.set_data_port(port_out, None, bus_name)

            if component_name == "BPLReader":
                pass
            for input_data in input_data_list:
                param_name = input_data[0]
                param_value = input_data[1]
                for bus_name in connect_bus_list:
                    tmp = "Setting input data.[Component='%s', " % component_name
                    tmp += "Bus='%s', PortName='%s', " % (bus_name, param_name)
                    tmp += "PortValue=%s]" % str(param_value)
                    self.__logger.debug(tmp)
                    self.__data_manager.set_data_port(param_name, param_value, bus_name)
            if order is not None:
                self.__object_map_list.append({"Order": order, "ComponentName": component_name, "ClsObj": cls_obj})

        if len(self.__object_map_list):
            self.__object_map_list.sort(lambda x, y: cmp(int(x["Order"]), int(y["Order"])))

            component_list = []
            for object_map in self.__object_map_list:
                component_list.append(object_map["ClsObj"])

            if len(component_list):
                self.__logger.info("%d plug-in(s) loaded." % len(component_list))
                return component_list

        return None

"""
CHANGE LOG:
-----------
$Log: config_manager.py  $
Revision 1.2 2020/03/31 10:14:10CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:06CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
