import logging
from opcua import Server, ua, Node
from mtppy.communication_object import OPCUACommunicationObject
from mtppy.service import Service
from mtppy.suc_data_assembly import SUCDataAssembly, SUCActiveElement, SUCIndicatorElement, SUCOperationElement
from mtppy.mtp_generator import MTPGenerator

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class OPCUAServerPEA:
    def __init__(self, mtp_generator: MTPGenerator = None, endpoint: str = 'opc.tcp://127.0.0.1:4840/'):
        """
        Defines an OPC UA server for PEA.

        Args:
            mtp_generator (MTPGenerator): Instance of an MTP generator.
            endpoint (str): Endpoint of the OPC UA server.
        """
        self.service_set: dict[str, Service] = {}
        self.active_elements: dict[str, SUCActiveElement] = {}
        self.indicator_elements: dict[str, SUCIndicatorElement] = {}
        self.operation_elements: dict[str, SUCOperationElement] = {}
        self.custom_data_assembly_sets: dict[str, dict[str, SUCDataAssembly]] = {}
        self.endpoint: str = endpoint
        self.opcua_server: Server = None
        self.opcua_ns: int = 3
        self.subscription_list = SubscriptionList()
        self._init_opcua_server()
        self.mtp: MTPGenerator = mtp_generator

        self._folders = ['configuration_parameters', 'procedures', 'procedure_parameters',
                         'process_value_ins', 'report_values', 'process_value_outs']
        """Folders that are created in the OPC UA server if found in a data assembly
        even if they are not of type SUCDataAssembly."""

        self._leaves = ['op_src_mode', 'state_machine', 'procedure_control', 'locks']
        """Folders that are created in the OPC UA server if found in a data assembly
        even if they are not of type SUCDataAssembly.

        No subfolders are created for them."""

    def add_service(self, service: Service):
        """
        Add a service to the PEA.

        Args:
            service (Service): Service instance.
        """
        self.service_set[service.tag_name] = service

    def add_active_element(self, active_element: SUCActiveElement):
        """
        Add an active element to the PEA.

        Args:
            active_element (SUCActiveElement): Active element (e.g., AnaVlv, BinVlv, etc.).
        """
        self.active_elements[active_element.tag_name] = active_element

    def add_indicator_element(self, indicator_element: SUCIndicatorElement):
        """
        Add an indicator element to the PEA.

        Args:
            indicator_element (SUCIndicatorElement): Indicator element.
        """
        self.indicator_elements[indicator_element.tag_name] = indicator_element

    def add_operation_element(self, operation_element: SUCOperationElement):
        """
        Add an operation element to the PEA.

        Args:
            operation_element (SUCOperationElement): Operation element.
        """
        self.operation_elements[operation_element.tag_name] = operation_element

    def add_custom_data_assembly_set(self, root_folder_name: str, data_assembly_set: dict[str, SUCDataAssembly]):
        """
        Add a custom data assembly to the PEA.

        Args:
            root_folder_name (str): Root folder name for the custom data assembly.
            data_assembly (dict[str, SUCDataAssembly]): Custom data assembly instance.
                Has to be a dictionary with folder names as keys and SUCDataAssembly instances as values.
                If name is '', the data assembly is added to the root of the PEA.
        """

        if root_folder_name in self.custom_data_assembly_sets:
            raise ValueError(f"Data assembly with tag name '{root_folder_name}' already exists.")
        if not isinstance(data_assembly_set, dict) or data_assembly_set.__len__() == 0:
            raise ValueError("Data assembly set must be a non-empty dictionary.")
        if not isinstance(next(iter(data_assembly_set)), str):
            raise TypeError("Data assembly set keys must be strings.")
        if not isinstance(next(iter(data_assembly_set.values())), SUCDataAssembly):
            raise TypeError("Data assembly set values must be instances of SUCDataAssembly.")

        root_folder_name = (next(iter(data_assembly_set)) if root_folder_name == ''
                            else root_folder_name)
        self.custom_data_assembly_sets[root_folder_name] = data_assembly_set

    def add_folders(self, folders: list[str]):
        """
        Folders that are created in the OPC UA server if found in a opcua object.
        even if they are not of type SUCDataAssembly.

        Args:
            folders (list[str]): List of folder names.
        """
        self._folders.extend(folders)

    def add_leaves(self, leaves: list[str]):
        """
        Leaves that are created in the OPC UA server if found in a opcua object.
        even if they are not of type SUCDataAssembly.

        No Subfolders are created for them.

        Args:
            leaves (list[str]): List of leaf names.
        """
        self._leaves.extend(leaves)

    def _init_opcua_server(self):
        """
        Initializes an OPC UA server and sets the endpoint.
        """
        _logger.info(f'Initialisation of OPC UA server: {self.endpoint}')
        self.opcua_server = Server()
        self.opcua_server.set_endpoint(self.endpoint)
        # self.opcua_ns = self.opcua_server.register_namespace('namespace_idx')

    def get_opcua_server(self):
        """
        Get an OPC UA server instance object.

        Returns:
            Server: OPC UA server instance.
        """
        return self.opcua_server

    def get_opcua_ns(self):
        """
        Get an OPC UA server namespace index.

        Returns:
            int: Namespace index.
        """
        return self.opcua_ns

    def run_opcua_server(self):
        """
        Starts the OPC UA server instance.
        """
        self.opcua_server.start()
        self._build_opcua_server()
        self._start_subscription()

    def set_services_in_idle(self):
        """
        Sets all services to idle state.
        """
        for service in self.service_set.values():
            service._init_idle_state()

    def _build_opcua_server(self):
        """
        Creates an OPC UA server instance including required nodes according to defined data assemblies.
        """
        _logger.info(f'Adding OPC UA nodes to the server structure according to the PEA structure:')

        # initiate a new MTP that will be added to InstanceHierarchy: ModuleTypePackage
        if self.mtp:
            self.mtp.add_module_type_package('1.0.0', name='mtp_test', description='')

        # add InternalElement opcua server to ModuleTypePackage/CommunicationSet/SourceList
        if self.mtp:
            self.mtp.add_opcua_server(self.endpoint)

        # add service elements
        if self.service_set.__len__() > 0:
            self._create_opcua_element(self.service_set, "services")

        # add active, indicator and operation elements
        if self.active_elements.__len__() > 0:
            self._create_opcua_element(self.active_elements, "active_elements")
        if self.indicator_elements.__len__() > 0:
            self._create_opcua_element(self.indicator_elements, "indicator_elements")
        if self.operation_elements.__len__() > 0:
            self._create_opcua_element(self.operation_elements, "operation_elements")

        # add custom data assemblies
        for root_folder_name, data_assembly_set in self.custom_data_assembly_sets.items():
            _logger.info(f'- custom data assembly {root_folder_name}')
            # if root_folder_name is the same as the first key add to root
            if root_folder_name == next(iter(data_assembly_set)):
                ns = self.opcua_ns
                server = self.opcua_server.get_objects_node()
                self._create_opcua_objects_for_folders(
                    data_assembly_set[root_folder_name], f"ns={ns};s={root_folder_name}", server, root_folder_name)
            else:
                self._create_opcua_element(data_assembly_set, root_folder_name)

                # add SupportedRoleClass to all InternalElements
        if self.mtp:
            self.mtp.apply_add_supported_role_class()

        # export manifest.aml
        if self.mtp:
            _logger.info(f'MTP manifest export to {self.mtp.export_path}')
            self.mtp.export_manifest()

    def _create_opcua_element(self, elements: dict[str, SUCDataAssembly], folder_name: str):
        """
        Create OPC UA nodes for a specific element type (active elements, indicator elements, operation elements).

        Args:
            elements (dict[str, SUCDataAssembly]): Dictionary of elements.
            folder_name (str): Name of the folder to create in the OPC UA server.
        """
        ns = self.opcua_ns
        server = self.opcua_server.get_objects_node()
        element_node_id = f'ns={ns};s={folder_name}'
        element_node = server.add_folder(element_node_id, folder_name)
        _logger.info(f'- {folder_name}')
        for element in elements.values():
            _logger.info(f'-- element {element.tag_name}')
            self._create_opcua_objects_for_folders(element, element_node_id, element_node)

    def _create_opcua_objects_for_folders(self, data_assembly: SUCDataAssembly,
                                          parent_opcua_prefix: str, parent_opcua_object: Node,
                                          name: str = None):
        """
        Iterates over data assemblies to create OPC UA folders.

        Args:
            data_assembly (SUCDataAssembly): Data assembly.
            parent_opcua_prefix (str): Prefix to add in front of the data assembly tag.
            parent_opcua_object: Parent OPC UA node where the data assembly is added.
            name (str): Name of the data assembly. If None, the tag name of the data assembly is used.
        """
        if name is None:
            name = data_assembly.tag_name
        da_node_id = f'{parent_opcua_prefix}.{name}'
        da_node = parent_opcua_object.add_folder(da_node_id, name)
        _logger.debug(f'OPCUA Folder: {da_node_id}, Name: {name}')

        # type of data assembly (e.g. services, active_elements, procedures etc.)
        da_type = parent_opcua_prefix.split('=')[-1].split('.')[-1]

        # create instance of  ServiceControl, HealthStateView, DIntServParam etc.
        if self.mtp:
            instance = self.mtp.create_instance(data_assembly, da_node_id)
        else:
            instance = None

        if self.mtp:
            link_id = self.mtp.random_id_generator()
            if da_type == 'services' or da_type in self._folders:
                link_id = self.mtp.create_components_for_services(data_assembly, da_type)
        else:
            link_id = None

        # Add attributes of data assembly
        if hasattr(data_assembly, 'attributes'):
            self._create_opcua_objects_for_leaves(data_assembly, da_node_id, da_node, instance)

        # Find any variable of data_assembly that is of type SUCDataAssembly
        # and create corresponding folders and leaves for it
        for variable_name, value in self.__get_objects_attributes(data_assembly).items():
            if not isinstance(value, SUCDataAssembly) and variable_name not in self._folders + self._leaves:
                continue
            if name in self._leaves:
                continue  # do not create folders for leaves
            folder_name = value.tag_name if hasattr(value, 'tag_name') else variable_name
            self._create_opcua_objects_for_folders(value, da_node_id, da_node, folder_name)

        # create linked obj between instance and service component
        if self.mtp:
            self.mtp.add_linked_attr(instance, link_id)

    def _create_opcua_objects_for_leaves(self, opcua_object: SUCDataAssembly, parent_opcua_prefix: str, parent_opcua_object: Node, par_instance):
        """
        Iterates over end objects (leaves) of data assemblies to create corresponding OPC UA nodes.

        Args:
            opcua_object: Element of a data assembly that an OPC UA node is created for.
            parent_opcua_prefix (str): Prefix to add in front of the data assembly tag.
            parent_opcua_object: Parent OPC UA node where the data assembly is added.
            par_instance: Parameter instance.
        """
        for attr in opcua_object.attributes.values():
            attribute_node_id = f'{parent_opcua_prefix}.{attr.name}'

            # We attach communication objects to be able to write values on opcua server on attributes change
            opcua_type = self._infer_data_type(attr.type)
            opcua_node_obj: Node = parent_opcua_object.add_variable(attribute_node_id, attr.name, attr.init_value,
                                                                    varianttype=opcua_type)
            _logger.debug(
                f'OPCUA Node: {attribute_node_id}, Name: {attr.name}, Value: {attr.init_value}')
            opcua_node_obj.set_writable(False)
            opcua_comm_obj = OPCUACommunicationObject(opcua_node_obj, node_id=opcua_node_obj)
            attr.attach_communication_object(opcua_comm_obj)

            if self.mtp:
                linked_id = self.mtp.random_id_generator()  # create linked-id for opc ua node
                # add opc ua node and its attributes to ModuleTypePackage/CommunicationSet/SourceList/OPCUAServer
                self.mtp.add_external_interface(attribute_node_id, self.opcua_ns, linked_id)
            else:
                linked_id = None

            """
            add attributes of data assembly to corresponding instance under InstanceList
            e.g.: attributes of services belong to InstanceList/ServiceControl

            exception: some attributes of procedure ('ProcedureId', 'IsSelfCompleting', 'IsDefault') should be
            added to InstanceHierarchy_Service/service/procedure. The other attributes of procedure should belong to
            InstanceList/HeathStateView
            """
            if type(opcua_object).__name__ == 'Procedure' and attr.name in ['ProcedureId', 'IsSelfCompleting', 'IsDefault']:
                pass
            else:
                if self.mtp:
                    self.mtp.add_attr_to_instance(
                        par_instance, attr.name, attr.init_value, linked_id)

            # We subscribe to nodes that are writable attributes
            if attr.sub_cb is not None:
                opcua_node_obj.set_writable(True)
                self.subscription_list.append(opcua_node_obj, attr.sub_cb)

    @staticmethod
    def _infer_data_type(attribute_data_type):
        """
        Translate a Python data type to a suitable OPC UA data type.

        Args:
            attribute_data_type (type): Python variable type.

        Returns:
            ua.VariantType: OPC UA data type.
        """
        if attribute_data_type == int:
            return ua.VariantType.Int64
        elif attribute_data_type == float:
            return ua.VariantType.Float
        elif attribute_data_type == bool:
            return ua.VariantType.Boolean
        elif attribute_data_type == str:
            return ua.VariantType.String
        else:
            return None

    def _start_subscription(self):
        """
        Subscribes to defined OPC UA nodes.
        """
        handler = Marshalling()
        handler.import_subscription_list(self.subscription_list)
        sub = self.opcua_server.create_subscription(500, handler)
        nodeid_list = self.subscription_list.get_nodeid_list()
        if nodeid_list is None:
            _logger.warning('No subscriptions to OPC UA nodes defined.')
            return
        handle = sub.subscribe_data_change(nodeid_list)

    def __get_objects_attributes(self, object) -> dict:
        """
        Get all attributes of the given object.

        Args:
            object: any python object.
        """
        if isinstance(object, dict):
            return object
        if isinstance(object, list):
            # return a dictionary with index as key
            return {f'{i}': item for i, item in enumerate(object)}
        try:
            return vars(object)
        except TypeError:
            return {}


class SubscriptionList:
    def __init__(self):
        """
        Subscription list that contains all OPC UA nodes that PEA must subscribe to.
        """
        self.sub_list = {}

    def append(self, node_id, cb_value_change):
        """
        Add a subscription entity.

        Args:
            node_id: OPC UA node.
            cb_value_change (function): Callback function for a value change.
        """
        identifier = node_id.nodeid.Identifier
        self.sub_list[identifier] = {'node_id': node_id, 'callback': cb_value_change}

    def get_nodeid_list(self):
        """
        Extract a list of node ids in the subscription list.

        Returns:
            list: List of node ids.
        """
        if len(self.sub_list) == 0:
            return None
        else:
            node_id_list = []
            for node_id in self.sub_list.values():
                node_id_list.append(node_id['node_id'])
            return node_id_list

    def get_callback(self, node_id):
        """
        Get a callback function for a specific OPC UA node.

        Args:
            node_id: OPC UA node id.

        Returns:
            function: Callback function.
        """
        identifier = node_id.nodeid.Identifier
        if identifier in self.sub_list.keys():
            return self.sub_list[identifier]['callback']
        else:
            return None


class Marshalling(object):
    def __init__(self):
        """
        Supplementary class for marshalling OPC UA subscriptions.
        """
        self.subscription_list = None

    def import_subscription_list(self, subscription_list: SubscriptionList):
        """
        Import a subscription list.

        Args:
            subscription_list (SubscriptionList): Subscription list.
        """
        self.subscription_list = subscription_list

    def datachange_notification(self, node, val, data):
        """
        Executes a callback function if data value changes.

        Args:
            node: OPC UA node.
            val: Value after change.
            data: Not used.
        """
        callback = self.find_set_callback(node)
        if callback is not None:
            try:
                callback(val)
            except Exception as exc:
                pass
                _logger.warning(f'Something wrong with callback {callback}: {exc}')

    def find_set_callback(self, node_id):
        """
        Finds a callback function to a specific OPC UA node by nodeid.

        Args:
            node_id: Node id.

        Returns:
            function: Callback function.
        """
        return self.subscription_list.get_callback(node_id)
