from Timeline.Server.Constants import TIMELINE_LOGGER, LOGIN_SERVER, WORLD_SERVER
from Timeline.Utils.Events import Event, PacketEventHandler, GeneralEvent
from Timeline.Database.DB import Penguin

from twisted.internet.defer import inlineCallbacks, returnValue

from collections import deque
import logging
from time import time

@PacketEventHandler.XTPacketRule('s', 'm#sm', WORLD_SERVER)
def SendMessageRule(data):
	return [[int(data[2][0]), str(data[2][1])], {}]

@PacketEventHandler.onXT('s', 'm#sm', WORLD_SERVER)
def handleSendMessage(client, _id, message):
	if not client['id'] == _id:
		return

	message = message.strip(' ').replace('|', '\|')

	GeneralEvent.call('before-message', client, message)

	if client['muted']:
		GeneralEvent.call('after-message-muted', client, message)
		return

	client['room'].send('sm', _id, message)

	GeneralEvent.call('after-message', client, message)