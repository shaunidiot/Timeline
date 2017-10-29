'''
Timeline - An AS3 CPPS emulator, written by dote, in python. Extensively using Twisted modules and is event driven.
Login.py handles the incoming XML Packet used to login to server. Packets may not necessarily be `login packet`
'''
from Timeline.Server.Constants import TIMELINE_LOGGER, LOGIN_SERVER, WORLD_SERVER
from Timeline import Username, Password
from Timeline.Utils.Events import Event, PacketEventHandler, GeneralEvent

from twisted.internet.defer import inlineCallbacks, returnValue

from collections import deque
import logging

logger = logging.getLogger(TIMELINE_LOGGER)

@PacketEventHandler.onXML('verChk', LOGIN_SERVER)
@PacketEventHandler.onXML('verChk', WORLD_SERVER)
def APIVersionCheck(client, version):
	if version != 153:
		client.send(client.PacketHandler.buildXML({"msg" : {'t' : 'sys', 'body' : {'action' : 'apiKO', 'r' : '0'} } }))
		return client.disconnect()

	client.send(client.PacketHandler.buildXML({"msg" : {'t' : 'sys', 'body' : {'action' : 'apiOK', 'r' : '0'} } }))
	if client.handshakeStage < 1:
		client.handshakeStage = 1 # Just a note that API version is verified!

@PacketEventHandler.onXML('rndK', LOGIN_SERVER, p_r = False)
@PacketEventHandler.onXML('rndK', WORLD_SERVER, p_r = False)
def GetPenguinRandomKey(client, body):
	client.send(client.PacketHandler.buildXML({"msg" : {'t' : 'sys', 'body' : {'action' : 'rndK', 'r' : '-1', 'k' : list([client.CryptoHandler.randomKey]) } } }))

@PacketEventHandler.onXML('login', LOGIN_SERVER)
@inlineCallbacks
def HandlePrimaryPenguinLogin(client, user, passd):
	exist = yield client.db_penguinExists('username', user)
	
	if not exist:
		client.send("e", 101)
		returnValue(client.disconnect())
	
	client.penguin.username = Username(user, client) 
	yield client.db_init()
	
	client.penguin.password = Password(client.dbpenguin.password, client)
	if not client.checkPassword(passd):
		client.send('e', 101)
		returnValue(client.disconnect())
		
	if client.banned():
		returnValue(0)
		
	client.penguin.swid = client.dbpenguin.swid
	
	key = client.CryptoHandler.confirmHash()
	confh = client.CryptoHandler.bcrypt(key)
	fkey = client.CryptoHandler.md5(key)
	
	client.engine.redis.server.set("conf:{0}".format(client.dbpenguin.ID), key, 15*60)
	
	world = list()
	w = yield client.engine.redis.getWorldServers()
	
	for k in w:
		p = w[k]
		bars = int(int(p['population']) * 5 / int(p['max']))
		world.append("{},{}".format(k, bars))
		
	world = '|'.join(world)
	player_data = "{}|{}|{}|{}|NULL|45|2".format(client.dbpenguin.ID, client.dbpenguin.swid, client['username'], client.CryptoHandler.bcrypt(key))
	email = client.dbpenguin.email[0] + '***@' + client.dbpenguin.email.split('@')[1]
	
	client.send('l', player_data, confh, fkey, world, email)
	
	returnValue(client.disconnect())
	
def init():
	logger.debug('Login Server::Login initiated!')
	logger.debug('World Server::Login initiated!')

print 'shit', 1