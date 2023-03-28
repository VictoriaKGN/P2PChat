from enum import IntEnum

class UDPMessage:
    def __init__(self, messageID, senderID, senderUsername, message):
        self.messageID = messageID
        self.senderID = senderID
        self.senderUsername = senderUsername
        self.message = message

class TCPMessage:
    def __init__(self, messageID, senderID, message):
        self.messageID = messageID
        self.senderID = senderID
        self.message = message

class MessageID(IntEnum):
    ONLINE = 1
    OFFLINE = 2
    START = 3
    INIT = 4
    PERSONAL = 5