## Definately Not Discord - Local Peer-to-Peer Chat

Victoria Kogan 7886506\
COMP 3010 - Distributed Computing\
Winter 2023\
University of Manitoba

## Experience

Developing this local peer-to-peer decentralized chat system has been an interesting experience. 
A significant portion of the time was dedicated to designing the architecture as there were a lot of components to consider while coming up with ways to produce the least amount of message exchanges to avoid cluttering the traffic. 
While it may seem that using UDP for personal message exchanges would be easier to implement, there are multiple downsides under the surface. 
Examples of such issues are the possibility of lost packets and not knowing if a message has been received, making it difficult to maintain a single source of truth. 
Therefore, initiating a TCP connection with other peers in each session was crucial, making it necessary to send a UDP message before establishing a TCP connection so that the other peer will be ready to receive the message. 
To make the system as safe as possible, asymmetric RSA keys were introduced. 
There were some challenges, such as flattening them and distributing them for each connection, that I was able to overcome, but others, such as the delay it takes to produce them, had to be left unfixed as it is out of the scope of distributed computing. 
Another issue that rose was being able to differentiate each peer. 
As the peers are unaware of other peers’ usernames and there is no server that keeps track of usernames, it was essential to produce a unique ID for each peer when they open the app for the first time ever. 
This is one of the many components that would have been otherwise handled by a centralized, making it challenging to efficiently implement a peer. 
One of the toughest aspects of this app was managing multiple threads that listen, send, and update the UI, where I had to introduce a mediator class that handles shared queues of actions between the socket end and the UI end. 
Despite all those obstacles, I believe this project offered me more knowledge than a term paper could have, as the best way to learn things is by hands-on doing them.
There were other features that I would have loved to implement but time unfortunately did not permit me to. 
Although not having a server to handle communications makes it difficult, this system has great potential as it is more secure than centralized systems.


## Architecture

![Alt text](/Paperwork/Images/OnlineAck.png)

![Alt text](/Paperwork/Images/TCPEncryptedMsg.png)

![Alt text](/Paperwork/Images/Offline.png)


## Possible Features

1.	Group chats – 2 options of implementation:
    1. UDP to all chat members, issues with packet loss.
    2. TCP but having one member as chat admin to which all other members connect to and messages pass them, issues when they go offline.
2.	Sending images or files
    * Requires to be flattened just like RSA keys are flattened and sent.
3.	Reconnection
    *	Requires writing all peers currently connected to the database, so when the app crashes and opens again, it would know whom to connect to.
    * As some connections were through the main TCP server, would probably require connecting to the other peers’ servers as clients instead.
4.	Threads for message handling
    *	Wanted to implement this, but time restricted.
    *	Need to open a new thread for each incoming message handling, so messages would be handled faster. 
    *	Will need to introduce locks as multiple threads could be writing and fetching things from shared queues and shared variables in the Peer class (mediator).
