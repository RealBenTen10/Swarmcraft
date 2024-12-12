'''
start server and control simulation here
'''

from agent import Agent, Behavior
from javascript import require, On, off
mineflayer = require('mineflayer')

agentCount = 10
agents = []

# behaviors can be global
health_change = Behavior('health', lambda a, *info: a.bot.chat('health changed'))

for i in range(agentCount):
    new_agent = Agent(i)
    while not new_agent.ready: pass
    agents.append(new_agent)
    health_change.bind(new_agent)
    # or local
    # when dealing with bot state, behaviors should get variables from a, not have them passed from the outside
    new_agent.add_behavior(str(new_agent.uid) + 'otherhealth', 'health', (lambda a, *info: a.bot.chat(str(a.uid))))
    new_agent.disable_behavior(str(new_agent.uid) + 'otherhealth')

print("spawned all agents")
health_change.disable()
agents[0].enable_behavior('0otherhealth')
