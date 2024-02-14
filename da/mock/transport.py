from da.common import NodeId, Certificate

class Message:
    def __init__(self, sender, receiver, message):
        self.sender = sender
        self.receiver = receiver
        self.message = message

class Transport:
    def __init__(self, identifier, message_handler=None):
        self.identifier = identifier
        self.inbound_messages = []
        self.outbound_messages = []
        self.neighbors = {}
        self.message_handler = message_handler

    def send_message(self, receiver, message):
        message = Message(self.identifier, receiver.identifier, message)
        self.outbound_messages.append(message)
        receiver.receive_message(message)

    def receive_message(self, message):
        self.inbound_messages.append(message)
        if self.message_handler:
            self.message_handler(self, message)

    def connect(self, other_node):
        self.neighbors[other_node.identifier] = other_node

