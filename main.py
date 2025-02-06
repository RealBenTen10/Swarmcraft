'''
start server and control simulation here
'''
from time import sleep

from javascript import require
from agent import Agent

mineflayer = require('mineflayer')

bot = mineflayer.createBot({
    "host": "localhost",
    "port": "25565",
    "username": "bot",
})
agent = Agent(bot)

while True:
    agent.update()
    sleep(0.1)
