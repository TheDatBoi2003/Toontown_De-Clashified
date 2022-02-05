from direct.directnotify import DirectNotifyGlobal
from direct.showbase.DirectObject import DirectObject

from toontown.battle.SuitBattleGlobals import DMG_DOWN_STATUS


class StatusCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('StatusCalculatorAI')

    def __init__(self, battle):
        DirectObject.__init__(self)
        self.lostStatusesDict = {}              # Updated when a suit loses a status for a round
        self.battle = battle
        self.accept('post-suit', self.postSuitStatusRounds)
        self.accept('init-round', self.__resetFields)

    def cleanup(self):
        self.ignoreAll()

    def removeStatus(self, suit, status=None, statusName=None):
        if statusName:
            status = suit.getStatus(statusName)
        elif status:
            statusName = status['name']

        if not status:
            self.notify.debug('No status to remove!')
            return

        lostStatuses = self.getLostStatuses(statusName)
        lostStatuses[suit] = status
        suit.b_removeStatus(statusName)
        self.notify.debug('%s just lost its %s status.' % (suit.doId, statusName))

    def getLostStatuses(self, statusName):
        if statusName not in self.lostStatusesDict:
            self.lostStatusesDict[statusName] = {}
        return self.lostStatusesDict[statusName]

    def postSuitStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(DMG_DOWN_STATUS)
            if removedStatus:
                self.removeStatus(activeSuit, removedStatus)

    def __resetFields(self):
        self.lostStatusesDict = {}
