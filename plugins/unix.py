#!/usr/bin/env python

from twisted.internet import protocol
from logging import debug, error, info

class MyP(protocol.ProcessProtocol):
    def __init__(self, bot, to):
        self.bot = bot
        self.to = to
    def connectionMade(self):
        debug('connect to terminal')
        pass
    def outReceived(self, data):
        self.bot.sendMsg(self.to, data.rstrip())

def init():
    return (u'ping', ) 

def ping(bot, to, arg):
    p = MyP(bot, to)

    if len(arg) < 1:
        bot.sendMsg(to, 'ping <host> <num>')
    else:
        ip = arg[0]
        if len(arg) > 1:
            num = int(arg[1])
        else:
            num = 5
        bot.reactor.spawnProcess(p, '/bin/ping', args=['ping', '-c', str(num), ip])
