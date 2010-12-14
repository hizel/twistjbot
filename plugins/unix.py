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
        self.bot.sendMsg(self.to, data)

def init():
    return (u'ping', ) 

def ping(bot, to, a):
    p = MyP(bot, to)
    debug('%s %s' % (a[0],type(a[0])))
    bot.reactor.spawnProcess(p, '/bin/ping', args=['ping', '-c 5', a[0]])
