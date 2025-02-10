# class for pooling agents, and maintaining lists of active and ready agents
import uuid
from typing import List, Callable, Any
from javascript import require

import util

mineflayer = require('mineflayer')

log_chat = True

class Pooler:
    def __init__(self):
        self.active_agents = []

    def create_agent(self, username: str, agent_template: Callable[[..., ...], Any], host='localhost', port='25565'):
        # if we have any bots already using the username, throw an error
        for agent in self.active_agents:
            if agent.sensing.get_username() == username:
                raise RuntimeError(f"Agent {agent.sensing.get_username()} already exists")

        b = mineflayer.createBot({
            "host": host,
            "port": port,
            "username": username,
        })
        a = agent_template(b, uuid.uuid1())
        self.active_agents.append(a)
        return a

    def update_all_agents(self):
        for agent in self.active_agents:
            if agent.sensing.connected:
                agent.update()

    def get_active_agents(self):
        return self.active_agents

    # internal message sending
    def send_message(self, sender, message, recipient=None, max_distance=-1):
        if log_chat:
            print(f'<{sender}> to', 'everyone:' if recipient is None else f'<{recipient}>:', message)
        # no recipient? send to everyone, append to their chat queues
        if recipient is None:
            for agent in self.active_agents:
                if max_distance != -1:
                    if util.dist_sqr(sender.sensing.get_position(), agent.sensing.get_position()) < max_distance ** 2:
                        agent.sensing.chat_queue.append({'username': sender.sensing.get_username(), 'message': message})
                else:
                    agent.sensing.chat_queue.append({'username': sender.sensing.get_username(), 'message': message})
        # send to only the recipient, append to their whisper queue
        else:
            for agent in self.active_agents:
                if agent.sensing.get_username() == recipient:
                    if max_distance != -1: # if a distance was given, only send to those within distance
                        if util.dist_sqr(sender.sensing.get_position(), agent.sensing.get_position()) < max_distance ** 2:
                            agent.sensing.whisper_queue.append({'username': sender.sensing.get_username(), 'message': message})
                    else:
                        agent.sensing.whisper_queue.append({'username': sender.sensing.get_username(), 'message': message})
                    break

pooler = Pooler()
