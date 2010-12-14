#!/usr/bin/env python

from optparse import OptionParser
from ConfigParser import ConfigParser
from sys import exit
from os.path import isfile

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.internet import reactor
from twisted.python.log import PythonLoggingObserver, startLogging
from twisted.words.xish import domish
from logging import basicConfig, DEBUG, debug, error, info

import os

class NoOpTwistedLogger:
    def flush(self):
        pass
    def write(self, x):
        pass

class Bot(object):
    def __init__(self, config):
        self.config = config

        PythonLoggingObserver().start()
        startLogging(NoOpTwistedLogger(), setStdout=False)

        if config.getboolean('bot', 'debug'):
            basicConfig(level=DEBUG, format='%(asctime)s %(levelname)s \
                    %(message)s')
        else:
            basicConfig(level=INFO, format='%(asctime)s %(levelname)s \
                    %(message)s')

        self.me = u'%s/%s' % (config.get('bot', 'jid'),
                             config.get('bot', 'resource'))


        self.commands = {}
        self._loadPlugins()

        self.jid = jid.JID(self.me)
        self.factory = client.XMPPClientFactory(self.jid,
                self.config.get('bot','pass'))
        self.factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        self.factory.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        self.factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        self.factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.initFailed)
        self.reactor = reactor
        self.reactor.connectTCP(self.config.get('bot','server'),
                self.config.getint('bot','port'), self.factory)
        self.reactor.run()

    def _loadPlugins(self):
        for fname in os.listdir('plugins/'):
            if fname.endswith('.py'):
                plugin_name = fname[:-3]
                if plugin_name != '__init__':
                    pluginstmp=__import__('plugins.'+plugin_name)
                    plugin = getattr(pluginstmp,plugin_name)
                    commands = plugin.init()
                    for c in commands:
                        self.commands.update({c : plugin})

    def connected(self, stream):
        self.stream = stream
        debug('connected')

    def disconnected(self, stream):
        self.stream = None
        debug('disconnected')

    def authenticated(self, stream):
        self.stream = stream
        debug('authenticated')
        presence = domish.Element(('jabber:client', 'presence'))
        presence.addElement('status').addContent('Online')
        stream.send(presence)
        stream.addObserver('/message', self.gotMessage)
        stream.addObserver('/presence', self.gotPresence)
        stream.addObserver('/iq', self.gotIq)
        stream.addObserver('/*', self.gotSomething)

    def initFailed(self, stream):
        debug('init error (%s)' % stream)

    def gotMessage(self, e):
        debug('got message %s', e.toXml())
        body = ''.join([''.join(x.children) for x in e.elements() if x.name == 'body'])
        if body != '':
            com = body.split()
            info('execute for command %s(%s) in %s' % (com[0], type(com[0]), self.commands))
            if com[0] not in self.commands:
                self.sendMsg(e['from'], 'unknown command')
            else:
                p = self.commands[com[0]]
                c = com[0]
                ec = getattr(p, c)
                ec(self, e['from'], com[1:])

    def sendMsg(self, to, msg):
        message = domish.Element(('jabber:client','message'))
        message['from'] = self.me
        message['to']   = to
        message['type'] = 'chat'
        message.addElement("body", "jabber:client", msg)
        xmlmsg = message.toXml().strip()
        debug('sended message >>> %s' % xmlmsg)
        self.stream.send(xmlmsg)

    def gotPresence(self, e):
        debug('got presence %s', e.toXml())
        if 'type' in e.attributes:
            t = e.attributes['type']
            if t == 'subscribe':
                self.stream.send(domish.Element(('jabber:client', 'presence'),
                    attribs= {
                        'from' : self.me,
                        'to'   : e.attributes['from'],
                        'type' : 'subscribed'
                        }))
            if t == 'unavailable':
                self.stream.send(domish.Element(('jabber:client', 'presence'),
                    attribs= {
                        'from' : self.me,
                        'to'   : e.attributes['from'],
                        'type' : 'unsubscribed'
                        }))

    def gotIq(self, e):
        debug('got presence %s', e.toXml())

    def gotSomething(self, e):
        debug('got something %s', e.toXml())

def main():
    parser = OptionParser("usage: %prog [options] config.file")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        print 'need one argument with configuration file name'
        exit()

    if not isfile(args[0]):
        print 'not exists config file %s' % (args[0])
        exit()

    config = ConfigParser()
    config.read(args[0])

    bot = Bot(config)

if __name__ == "__main__":
    main()
