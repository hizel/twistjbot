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

    def gotMessage(self, element):
        debug('got message %s', element.toXml())

    def gotPresence(self, element):
        debug('got presence %s', element.toXml())
        if 'type' in element.attributes:
            t = element.attributes['type']
            if t == 'subscribe':
                self.stream.send(domish.Element(('jabber:client', 'presence'),
                    attribs= {
                        'from' : self.me,
                        'to'   : element.attributes['from'],
                        'type' : 'subscribed'
                        }))
            if t == 'unavailable':
                self.stream.send(domish.Element(('jabber:client', 'presence'),
                    attribs= {
                        'from' : self.me,
                        'to'   : element.attributes['from'],
                        'type' : 'unsubscribed'
                        }))

    def gotIq(self, element):
        debug('got presence %s', element.toXml())

    def gotSomething(self, element):
        debug('got something %s', element.toXml())

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
