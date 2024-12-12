from javascript import require, On, off, Once, once
from typing import Callable, Any, Tuple

mineflayer = require('mineflayer')

'''
base agent class

bots respond to in-game events in hook form:
add a hook with:
Agent.bot.on('event', listener)
'''

class Agent:

    def __init__(self, uid, controller=None):
        self.bot = mineflayer.createBot({
            "host": "localhost",
            "port": "25565",
            "username": str(uid)
        })
        self.uid = uid
        self.controller = controller
        self.behaviors = {}
        # wait until we actually spawn to mark ourselves ready and set the rest of our hooks
        # initializer should block or wait until ready to call things on this agent's bot
        self.ready = False
        @Once(self.bot, 'spawn')
        def spawn(*args):
            self.ready = True
        # when we leave the server, we aren't ready anymore
        @On(self.bot, 'end')
        def end(*args):
            self.ready = False

    def add_behavior(self, key, trigger, handler, onetime=False):
        behavior = Behavior(trigger, handler, onetime)
        self.behaviors[key] = behavior
        behavior.bind(self)

    def enable_behavior(self, key):
        self.behaviors[key].enable()

    def disable_behavior(self, key):
        self.behaviors[key].disable()


class Behavior:
    def __init__(self, trigger, response: Callable[[Agent, tuple[Any, ...]], Any], onetime=False):
        self.trigger = trigger
        self.response = response # response expects an agent, then a tuple of information about the event, and can return anything
        self.enabled = True
        self.onetime = onetime

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def set_response(self, response: Callable[[Agent, tuple[Any, ...]], Any]):
        self.response = response

    def bind(self, agent):
        if self.onetime:
            @Once(agent.bot, self.trigger)
            def oneshot(*args):
                if self.enabled:
                    self.response(agent, args)
        else:
            @On(agent.bot, self.trigger)
            def handle(*args):
                if self.enabled:
                    self.response(agent, args)
