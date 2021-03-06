from Timeline.Server.Constants import TIMELINE_LOGGER, LOGIN_SERVER, WORLD_SERVER, GOLD_RUSH_DIGGABLES, PROBS
from Timeline import Username, Password
from Timeline.Utils.Events import Event, PacketEventHandler, GeneralEvent
from Timeline.Server.Room import Igloo

from twisted.internet.defer import inlineCallbacks, returnValue

from collections import deque
import logging
from time import time
import random

logger = logging.getLogger(TIMELINE_LOGGER)

@PacketEventHandler.onXT('s', 'j#js', WORLD_SERVER)
@inlineCallbacks
def handleJoinServer(client, _id, passd, lang):
	if _id != client.penguin.id or passd != client.penguin.password:
		client.send('e', 101)
		returnValue(client.disconnect())

	# User logged in!
	GeneralEvent.call("penguin-logged", client.selfRefer)
	yield client.engine.redis.server.hincrby('server:{}'.format(client.engine.id), 'population', 1)
	yield client.engine.redis.server.hmset("online:{}".format(client.penguin.id), {'joined' : 1})

	client.initialize()
	client.send('js', *(map(int, [client['member'] > 0, client['moderator'], client['epf']])))
	client.send('gps', client['id'], client['stampHandler'])

	client.canRecvPacket = True # Start receiving XT Packets

	member = int(client['member']) if int(client['member']) > 0 else 0
	client.send('lp', client, client['coins'], 0, 1024, int(time() * 1000), client['age'], 0, client['age'], member, '', client['cache'].playerWidget, client['cache'].mapCategory, client['cache'].igloo)
    
	client.engine.roomHandler.joinRoom(client, 'dojofire', 'name') # TODO Check for max-users limit

@GeneralEvent.on('onClientDisconnect')
def handleRemoveClient(client):
	if client['room'] is not None:
		client['room'].remove(client)

	if client['playing'] or client['game'] is not None or client['waddling']:
		client['game'].remove(client)

@GeneralEvent.on('onBuildClient')
def handleSetGoldenRushDigging(client):
	client.penguin.lastGoldenRushDig = int(time()) - 3

@PacketEventHandler.onXT('s', 'j#jr', WORLD_SERVER)
def handleJoinRoom(client, _id, x, y):
	client.penguin.x, client.penguin.y = x, y

	client.engine.roomHandler.joinRoom(client, _id, 'ext')

@PacketEventHandler.onXT('s', 'j#grs', WORLD_SERVER, p_r = False)
def handleRefreshRoom(client, data):
	if client['room'] is None:
		return

	client['room'].onAdd(client)

@PacketEventHandler.onXT('s', 'j#jp', WORLD_SERVER)
@inlineCallbacks
def handleJoinIgloo(client, _id, _type):
	room = yield client['iglooHandler'].createPenguinIgloo(_id)
	if room is None:
		returnValue(None)

	if client['room'] is not None:
		client['room'].remove(client)

	if client['waddling'] or client['playing']:
		client.send('e', 200)
	
	puffles = yield client['puffleHandler'].getPenguinPuffles(_id, _type == 'backyard')

	if _type == 'igloo':
		room.append(client)
		returnValue(None)

	if _type == 'backyard':
		if client['prevRooms'][-1] == room:
			if room.backyard is None:
				room.backyard = Igloo(client, room.ext_id, room.keyName, "{}'s Backyard".format(room.name), 150, False, False, None)
				room.backyard.type = 'backyard'
				room.backyard.opened = True
				room.backyard.owner = room.owner
				room.backyard._id = room._id

			if room.owner == client['id']:
				room.backyard.append(client)
				returnValue(None)

	client['prevRooms'][-1].append(client)

@PacketEventHandler.onXT('s', 'r#gtc', WORLD_SERVER, p_r = False)
def handleGetTotalPlayerCoins(client, data):
	client.send('gtc', client['coins'])

def random_picks(sequence, relative_odds):
	table = [ z for x, y in zip(sequence, relative_odds) for z in [x]*y ]
	while True:
		yield random.choice(table)

DIGGABLE = random_picks(GOLD_RUSH_DIGGABLES, PROBS)

@PacketEventHandler.onXT('s', 'r#cdu', WORLD_SERVER, p_r = False)
def handleGoldRushDig(client, data):
	cannotDig = max(0, 3 - int(time() - client['lastGoldenRushDig']))
	dcoin = DIGGABLE.next() * int(not cannotDig)
	if dcoin: 
		setattr(client.penguin, 'lastGoldenRushDig', int(time()))
		client['coins'] += dcoin

	client.send('cdu', dcoin, client['coins'])

def init():
	logger.debug('Join(j) Packet handlers initiated!')