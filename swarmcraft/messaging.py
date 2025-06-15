from swarmcraft import util

log_chat = True

class MessageServer:
    def __init__(self):
        self.clients = []

    def send(self, sender_agent, message, recipient_id: str=None, max_distance: int=None):
        if log_chat:
            print(f'<{sender_agent.id}> to', 'everyone:' if recipient_id is None else f'<{recipient_id}>:', message)
        if recipient_id is None:
            for client in self.clients:
                if max_distance is not None and util.dist_sqr(sender_agent.sensing.get_position(), client.sensing.get_position()) < max_distance ** 2:
                        client.sensing.messages.append(Message(sender_agent.id, client.id, message, False))
                else:
                    client.sensing.messages.append(Message(sender_agent.id, client.id, message, False))
        else:
            for client in self.clients:
                if client.id == recipient_id:
                    if max_distance is not None and util.dist_sqr(sender_agent.sensing.get_position(), client.sensing.get_position()) < max_distance ** 2:
                            client.sensing.messages.append(Message(sender_agent.id, client.id, message, True))
                    else:
                        client.sensing.messages.append(Message(sender_agent.id, client.id, message, True))
                    break

    def register(self, client_agent):
        self.clients.append(client_agent)

    def deregister(self, client_agent):
        self.clients.remove(client_agent)

class Message:
    def __init__(self, sender_id: str, receiver_id: str, contents: str, private: bool):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.contents = contents
        self.private = private

    def to_string(self):
        return str({
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'contents': self.contents,
            'private': self.private
        })

class Chat:
    def __init__(self, sender_username: str, receiver_username: str, contents: str, private: bool):
        self.sender_username = sender_username
        self.receiver_username = receiver_username
        self.contents = contents
        self.private = private

    def to_string(self):
        return str({
            'sender_username': self.sender_username,
            'receiver_username': self.receiver_username,
            'contents': self.contents,
            'private': self.private
        })
