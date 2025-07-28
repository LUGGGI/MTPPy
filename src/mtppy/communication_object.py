class OPCUACommunicationObject:
    def __init__(self, opcua_node_obj, node_id):
        """
        Represents a communication object for OPC UA for an attribute instance.

        Args:
            opcua_node_obj (object): OPC UA node object.
            node_id (str): OPCUA node id.
        """
        self.opcua_node_obj = opcua_node_obj
        self.node_id = node_id
        self.write_value_callback = opcua_node_obj.set_value
