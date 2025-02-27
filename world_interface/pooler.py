"""
agent pooling class
reduces spinup time for agents by maintaining pools of active/inactive agents, and provides methods for moving agents between these pools
except for agent creation, this class does not handle agent connect/disconnect actions
agents must ask the pooler to be removed when they disconnect
"""
import operator
from typing import Callable, Any
from javascript import require
from server.server import server
import shortuuid

import util

mineflayer = require('mineflayer')

log_chat = True

WORLD_CENTER = (0, 4, 0)
pooling_location = WORLD_CENTER
default_init_location = tuple(map(operator.add, WORLD_CENTER, (1, 0, 1)))

class Pooler:
    def __init__(self):
        self.active_agents = []
        self.agents_pool = []

    # initialize an agent and add them to the pool
    def create_agent(self, agent_factory: Callable[[..., ...], Any], uid=None, host='localhost', port='25565'):
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
            "username": str(uname), # new agents get a random username
        })
        a = agent_factory(b, uname) # and a random internal id
        if not a.sensing.connected:
            print("agent creation failed")
            return None
        self.reset_agent(a) # reset their stats
        server.send_command( # send them to the pooling area
            f'/tp {a.sensing.get_username()} {pooling_location[0]} {pooling_location[1]} {pooling_location[2]}')  # send them back to the pooling area
        self.agents_pool.append(a) # add them to the pool
        return a

    # activate the next available agent in the pool
    # returns the agent that was activated, or None if there were no agents in the pool
    # when an agent gets reactivated, they get a new internal id
    def activate_agent(self, init_location=default_init_location):
        if len(self.agents_pool) == 0:
            print(f"No agents left in pool")
            return
        a = self.agents_pool.pop(0)
        a.id = shortuuid.ShortUUID().random(length=8) # give them a new internal id
        server.send_command(f'/tp {a.sensing.get_username()} {init_location[0]} {init_location[1]} {init_location[2]}')
        self.active_agents.append(a)
        return a

    # reset an agent's stats
    def reset_agent(self, agent):
        agent.reset() # reset the agent
        # reset them serverside too
        server.send_command(f'/clear {agent.sensing.get_username()}') # clear their inventory
        server.send_command(f'/effect {agent.sensing.get_username()} instant_health 1 255') # heal them
        server.send_command(f'/effect {agent.sensing.get_username()} saturation 1 255') # reset their hunger
        print("reset agent")

    # take an agent from the active list to the pool, only if they were previously active
    # TODO this should also trigger a logging action maybe?
    def deactivate_agent(self, agent):
        if agent in self.active_agents:
            self.active_agents.remove(agent)
            self.agents_pool.append(agent)
        server.send_command(
            f'/tp {agent.sensing.get_username()} {pooling_location[0]} {pooling_location[1]} {pooling_location[2]}')  # send them back to the pooling area

    # remove an agent from the pool
    # doesn't disconnect
    def remove_agent(self, agent):
        if agent in self.active_agents:
            self.active_agents.remove(agent)
        elif agent in self.agents_pool:
            self.agents_pool.remove(agent)

    # run the update step on all active agents
    def update_active_agents(self):
        for agent in self.active_agents:
            agent.update()

    # internal message sending
    # uses internal ids instead of usernames
    def send_message(self, sender, message, recipient=None, max_distance=-1):
        if log_chat:
            print(f'<{sender}> to', 'everyone:' if recipient is None else f'<{recipient}>:', message)
        # no recipient? send to everyone, append to their chat queues
        if recipient is None:
            for agent in self.active_agents:
                if max_distance != -1:
                    if util.dist_sqr(sender.sensing.get_position(), agent.sensing.get_position()) < max_distance ** 2:
                        agent.sensing.chat_queue.append({'id': sender.id, 'message': message})
                else:
                    agent.sensing.chat_queue.append({'id': sender.id, 'message': message})
        # send to only the recipient, append to their whisper queue
        else:
            for agent in self.active_agents:
                if agent.sensing.get_username() == recipient:
                    if max_distance != -1: # if a distance was given, only send to those within distance
                        if util.dist_sqr(sender.sensing.get_position(), agent.sensing.get_position()) < max_distance ** 2:
                            agent.sensing.whisper_queue.append({'id': sender.id, 'message': message})
                    else:
                        agent.sensing.whisper_queue.append({'id': sender.id, 'message': message})
                    break

pooler = Pooler()
