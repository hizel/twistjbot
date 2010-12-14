#!/usr/bin/env python

def init():
    return (u'xping', ) 

def xping(bot, to, *args):
    bot.sendMsg(to, u'xpong')
