import util


log_chat = True

class MessageServer:
    def __init__(self):
        self.clients = []

    def send(self, sender_agent, message, recipient_id: str=None, max_distance: int=None):
        if log_chat:
            print(f'<{sender_agent.id}> to', 'everyone:' if recipient_id is None else f'<{recipient_id}>:', message)
        if recipient_id is None:
            for client in self.clients:
                if max_distance is not None:
                    if util.dist_sqr(sender_agent.sensing.get_position(), client.sensing.get_position()) < max_distance ** 2:
                        client.sensing.chat_queue.append({'id': sender_agent.id, 'message': message})
                else:
                    client.sensing.chat_queue.append({'id': sender_agent.id, 'message': message})
        else:
            for client in self.clients:
                if client.id == recipient_id:
                    if max_distance is not None:
                        if util.dist_sqr(sender_agent.sensing.get_position(), client.sensing.get_position()) < max_distance ** 2:
                            client.sensing.whisper_queue.append({'id': sender_agent.id, 'message': message})
                    else:
                        client.sensing.whisper_queue.append({'id': sender_agent.id, 'message': message})
                    break

    def register(self, client_agent):
        self.clients.append(client_agent)

    def deregister(self, client_agent):
        self.clients.remove(client_agent)

message_server = MessageServer()