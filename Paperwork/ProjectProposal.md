## Definately Not Discord - Local Peer-to-Peer Chat

Victoria Kogan 7886506\
COMP 3010 - Distributed Computing\
Winter 2023\
University of Manitoba

## Project Proposal

The goal of this project is to implement a peer-to-peer (P2P) chat service where users can directly communicate with each other without the need for a centralized server. 
Since there is no server that handles communication, the users act as both a client and a server. 
The chat will include a text-based direct messaging feature and might include a group chat feature if time permits. 
In order to ensure stable and reliable communication between peers, some connection error-handling mechanisms will be implemented.


Peer-to-peer chat service is an appropriate project for Distributed Computing because communication with a centralized server may not always be practical, making peer-to-peer communication the perfect solution. 
Creating a messaging service using a centralized server is pretty simple, but there are several disadvantages to such a service such as security and privacy concerns, but most importantly, the whole system is dependent on the middle server, meaning that there is a single point of failure. 
Implementing a peer-to-peer chat service that does not rely on a centralized server is a bit more challenging, but it tends to be more reliable and secure than a traditional client-server chat service since the communication is not being handled by a middle server. 
Therefore, a peer-to-peer service does not have a single point of failure.
