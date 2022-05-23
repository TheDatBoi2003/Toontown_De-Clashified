import copy
import random

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.directnotify import DirectNotifyGlobal

from otp.otpbase import OTPLocalizer
from toontown.toonbase import TTLocalizer

notify = DirectNotifyGlobal.directNotify.newCategory('ToonBattleGlobals')

TEST_STATUS = 'test'
MARKETING_STATUS = 'marketingPolicy'

ToonStatuses = [{'name': TEST_STATUS, 'levels': -1},
                {'name': MARKETING_STATUS, 'dmgCap': 0, 'comboCap': 0}]
ROUND_STATUSES = []


def genToonStatus(name):
    statusEffect = None
    for status in ToonStatuses:
        if name == status['name']:
            statusEffect = copy.deepcopy(status)
    return statusEffect


def makeStatusString(status):
    dg = PyDatagram()
    dg.addString(status['name'])
    if status['name'] in ROUND_STATUSES:
        dg.addInt16(status['rounds'])
    if status['name'] == TEST_STATUS:
        dg.addInt8(status['levels'])
    if status['name'] == MARKETING_STATUS:
        dg.addInt8(status['dmgCap'])
        dg.addInt8(status['comboCap'])

    return dg.getMessage()


def getStatusFromString(statusString):
    dg = PyDatagram(statusString)
    dgi = PyDatagramIterator(dg)
    status = genToonStatus(dgi.getString())
    if status['name'] in ROUND_STATUSES:
        status['rounds'] = dgi.getInt16()
    if status['name'] == TEST_STATUS:
        status['levels'] = dgi.getInt8()
    if status['name'] == MARKETING_STATUS:
        status['dmgCap'] = dgi.getInt8()
        status['comboCap']=dgi.getInt8()

    return status