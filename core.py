#!/usr/bin/env python

from optparse import OptionParser
from ConfigParser import ConfigParser
from sys import exit
from os.path import isfile

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.internet import reactor
from twisted.python.log import PythonLoggingObserver, startLogging
from twisted.words.xish import domish
from logging import basicConfig, DEBUG, INFO, debug, error, info

import os

class NoOpTwistedLogger:
    def flush(self):
        pass
    def write(self, x):
        pass

class Bot(object):
    def __init__(self, config):
        self.config = config

        if config.getboolean('bot', 'daemon'):
            from daemonize import become_daemon
            import fcntl
            self.logfile = config.get('daemon', 'logfile', '')
            if config.getboolean('bot', 'debug'):
                basicConfig(level=DEBUG, format='%(asctime)s %(levelname)s \
                        %(message)s', filename=self.logfile)
            else:
                basicConfig(level=INFO, format='%(asctime)s %(levelname)s \
                        %(message)s', filename=self.logfile)
            become_daemon()
            try:
                self.pidfile = open(config.get('daemon', 'pidfile'), 'w')
                fcntl.lockf(self.pidfile, fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.pidfile.write('%s' % (os.getpid()))
                self.pidfile.flush()
            except Exception, e:
                error('error create pid file %s' % str(e))

        else:
            if config.getboolean('bot', 'debug'):
                basicConfig(level=DEBUG, format='%(asctime)s %(levelname)s \
                        %(message)s')
            else:
                basicConfig(level=INFO, format='%(asctime)s %(levelname)s \
                        %(message)s')

        PythonLoggingObserver().start()
        startLogging(NoOpTwistedLogger(), setStdout=False)

        self.me = u'%s/%s' % (config.get('bot', 'jid'),
                             config.get('bot', 'resource'))


        self.commands = {}
        self.users = set(config.get('bot', 'users').split(','))
        self.ping_command    = config.get('commands', 'ping', '/bin/ping')
        self.arp_command     = config.get('commands', 'arp', '/usr/sbin/arp')
        self.netstat_command = config.get('commands', 'netstat', '/usr/bin/netstat')
        self.ifconfig_command = config.get('commands', 'ifconfig', '/sbin/ifconfig')
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
                    info('load plugin %s with commands %s' % (plugin_name,
                        commands))
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

    def _allowuser(self, u):
        j = jid.JID(u)
        if j.userhostJID().full() in self.users:
            return True
        return False

    def gotMessage(self, e):
        debug('got message %s', e.toXml())
        if not self._allowuser(e['from']):
            self.sendMsg(e['from'], 'Who\'s there?')
            return
        body = ''.join([''.join(x.children) for x in e.elements() if x.name == 'body'])
        if body != '' :
            com = body.split()
            j = jid.JID(e['from'])
            info('%s execute command %s' % (j.userhostJID().full(),com[0]))
            if com[0] not in self.commands:
                self.sendMsg(e['from'], 'fuck you :-)')
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
