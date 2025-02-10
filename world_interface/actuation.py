# class for doing things with the world, asynchronously
from time import sleep
from javascript import require
from world_interface.pooler import pooler

Vec3 = require('vec3').Vec3

class Actuation(object):
    def __init__(self, agent):
        # agent parts
        self.agent = agent

    # send a chat message to everyone
    def say(self, message: str):
        self.agent.bot.chat(message)

    # send a chat message to one player, regardless of distance
    def whisper(self, message: str, recipient_name: str):
        self.agent.bot.whisper(recipient_name, message)

    # chat methods using the pooler's chat - not rate-limited like the server
    def send_message(self, message: str, recipient_name: str):
        pooler.send_message(self.agent, message, recipient_name)

    def send_message_ranged(self, message: str, recipient_name: str, distance: float):
        pooler.send_message(self.agent, message, recipient_name, distance)

    def send_global_message(self, message: str):
        pooler.send_message(self.agent, message)

    def send_global_message_ranged(self, message: str, distance: float):
        pooler.send_message(self.agent, message, None, distance)

    # jump once
    def jump(self):
        self.agent.bot.setControlState('jump', True)
        self.agent.bot.setControlState('jump', False)

    # hold down a movement direction key for a given amount of time
    def move(self, direction: str, t: float):
        self.agent.bot.setControlState(direction, True)
        sleep(t)
        self.agent.bot.setControlState(direction, False)

    def key_down(self, direction: str):
        self.agent.bot.setControlState(direction, True)

    def key_up(self, direction: str):
        self.agent.bot.setControlState(direction, False)

    # stop all movement
    def stop(self):
        self.agent.bot.clearControlStates()

    # look at a specific point
    def look_at(self, position: tuple[float, float, float]):
        self.agent.bot.lookAt(Vec3(position[0], position[1], position[2]), True)

    # (yaw, pitch) in radians
    # yaw 0 is east
    # pitch 0 is forward
    # look in a direction
    def look(self, direction: tuple[float, float]):
        self.agent.bot.look(direction[0], direction[1], True)
