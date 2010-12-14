#!/usr/bin/env python

from optparse import OptionParser
from ConfigParser import ConfigParser
from sys import exit
from os.path import isfile

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.internet import reactor
from twisted.python.log import PythonLoggingObserver, startLogging
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


        self.jid = jid.JID(u'%s/%s' % (config.get('bot','jid'),
            config.get('bot','resource')))

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
        debug('authenticated')
        self.stream = stream

    def initFailed(self, stream):
        debug('init error (%s)' % stream)

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
