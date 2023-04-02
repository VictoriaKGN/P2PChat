from enum import IntEnum

class Message:
    def __init__(self, messageID, senderGUID, senderUsername, message):
        self.messageID = messageID
        self.senderGUID = senderGUID
        self.senderUsername = senderUsername
        self.message = message

class MessageID(IntEnum):
    ONLINE = 1
    OFFLINE = 2
    START = 3
    INIT = 4
    PERSONAL = 5

class Actions(IntEnum):
    MY_MESSAGE = 1
    PEER_MESSAGE = 2
    OFFLINE = 3
    ONLINE = 4
    USERNAME = 5
    INIT = 6