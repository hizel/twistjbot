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
    return (u'ping', u'arp', u'route', u'ifconfig') 

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
        bot.reactor.spawnProcess(p, bot.ping_command, args=['ping', '-c', str(num), ip])

def arp(bot, to, arg):
    p = MyP(bot, to)

    if len(arg) == 0:
        bot.reactor.spawnProcess(p, bot.arp_command, args=['arp', '-an'])

    if len(arg) > 1:
        if arg[0] == 'int' and len(arg) == 2:
            bot.reactor.spawnProcess(p, bot.arp_command, args=['arp', '-n', '-i', arg[1]])

def route(bot, to, arg):
    p = MyP(bot, to)

    if len(arg) == 0:
        bot.reactor.spawnProcess(p, bot.netstat_command, args=['netstat', '-rnW'])

def ifconfig(bot, to, arg):
    p = MyP(bot, to)

    if len(arg) == 0:
        bot.reactor.spawnProcess(p, bot.ifconfig_command, args=['ifconfig'])
