from enum import IntEnum

class Message:
    def __init__(self, id, sender, message):
        self.messageID = id
        self.sender = sender
        self.message = message

class MessageID(IntEnum):
    ONLINE = 1
    OFFLINE = 2
    START = 3