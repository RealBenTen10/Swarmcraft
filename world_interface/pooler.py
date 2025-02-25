# class for pooling agents, and maintaining lists of active and ready agents
import operator
from typing import Callable, Any
from javascript import require
from server import server
import shortuuid

import util

mineflayer = require('mineflayer')

log_chat = True

WORLD_CENTER = (0, 4, 0)
pooling_location = WORLD_CENTER
default_init_location = tuple(map(operator.add, WORLD_CENTER, (10, 0, 10)))

class Pooler:
    def __init__(self):
        self.active_agents = []
        self.agents_pool = []

    # should be called on server close - disconnects all the agents
    def disconnect_all_agents(self):
        for agent in self.agents_pool:
            agent.bot.quit()
        for agent in self.active_agents:
            agent.bot.quit()

    # initialize an agent and add them to the pool
    def create_agent(self, agent_template: Callable[[..., ...], Any], uid=None, host='localhost', port='25565'):
        if uid is None:
            uname = shortuuid.ShortUUID().random(length=8)
        else:
            for agent in self.active_agents:
                if agent.id == uid:
                    print("Agent with uid '" + uid + "' already exists")
                    return
            for agent in self.agents_pool:
                if agent.id == uid:
                    print("Agent with uid '" + uid + "' already exists")
                    return
            uname = uid
        b = mineflayer.createBot({
            "host": host,
            "port": port,
            "username": str(uname),
        })
        a = agent_template(b, uname)
        self.agents_pool.append(a)
        self.reset_agent(a)
        return a

    # activate the next available agent in the pool
    # returns the agent that was activated, or None if there were no agents in the pool
    def activate_agent(self, init_location=default_init_location):
        if len(self.agents_pool) == 0:
            print(f"No agents left in pool")
            return
        a = self.agents_pool.pop(0)
        server.send_command(f'/tp {a.sensing.get_username()} {init_location[0]} {init_location[1]} {init_location[2]}')
        self.active_agents.append(a)
        return a

    # deactivate an agent, reset them, and return them to the pool
    def reset_agent(self, agent):
        agent.reset() # reset the agent
        # reset them serverside too
        server.send_command(f'/clear {agent.sensing.get_username()}') # clear their inventory
        server.send_command(f'/effect {agent.sensing.get_username()} instant_health 1 255') # heal them
        server.send_command(f'/effect {agent.sensing.get_username()} saturation 1 255') # reset their hunger
        print("reset agent")

    def deactivate_agent(self, agent):
        if agent in self.active_agents:
            server.send_command(
                f'/tp {agent.sensing.get_username()} {pooling_location[0]} {pooling_location[1]} {pooling_location[2]}')  # send them back to the pooling area
            self.active_agents.remove(agent)
            self.agents_pool.append(agent)

    def update_active_agents(self):
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
