from direct.directnotify import DirectNotifyGlobal
from direct.showbase.DirectObject import DirectObject

from toontown.battle.SuitBattleGlobals import DMG_DOWN_STATUS


class StatusCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('StatusCalculatorAI')

    def __init__(self, battle):
        DirectObject.__init__(self)
        self.lostStatusesDict = {}
        self.battle = battle
        self.accept('post-suit', self.postSuitStatusRounds)

    def cleanup(self):
        self.ignoreAll()

    def removeStatus(self, suit, status=None, name=None):
        if name:
            status = suit.getStatus(name)
        elif status:
            name = status['name']

        if not status:
            return

        if name not in self.lostStatusesDict:
            self.lostStatusesDict[status['name']] = {}
        self.lostStatusesDict[status['name']][suit] = status
        suit.b_removeStatus(name)
        self.notify.info('%s just lost its %s status.' % (suit.doId, name))

    def getLostStatuses(self, statusName):
        return self.lostStatusesDict[statusName]

    def postSuitStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(DMG_DOWN_STATUS)
            if removedStatus:
                self.removeStatus(activeSuit, removedStatus)
