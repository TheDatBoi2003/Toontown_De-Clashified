import copy
import math

from direct.directnotify import DirectNotifyGlobal
from direct.showbase.MessengerGlobal import messenger
from panda3d.toontown import *

import SuitDNA
import SuitTimings
from toontown.battle import SuitBattleGlobals
from toontown.toonbase import TTLocalizer

TIME_BUFFER_PER_WPT = 0.25
TIME_DIVISOR = 100
DISTRIBUTE_TASK_CREATION = 0


class SuitBase:
    notify = DirectNotifyGlobal.directNotify.newCategory('SuitBase')

    def __init__(self):
        self.dna = None
        self.level = 0
        self.hardMaxHP = 1.5
        self.maxHP = 10
        self.currHP = 10
        self.isSkelecog = 0
        self.isExecutive = 0
        self.statuses = {}
        return

    def delete(self):
        pass

    def getStyleName(self):
        if hasattr(self, 'dna') and self.dna:
            return self.dna.name
        else:
            self.notify.error('called getStyleName() before dna was set!')
            return 'unknown'

    def getStyleDept(self):
        if hasattr(self, 'dna') and self.dna:
            return SuitDNA.getDeptFullname(self.dna.dept)
        else:
            self.notify.error('called getStyleDept() before dna was set!')
            return 'unknown'

    def getLevel(self):
        return self.level

    def setLevel(self, level):
        self.level = level
        self.updateName()
        self.updateHP()

    def getSkelecog(self):
        return self.isSkelecog

    def getExecutive(self):
        return self.isExecutive

    def getExecutiveTitle(self):
        if self.getExecutive() == 1:
            return TTLocalizer.SuitExecutiveTitle
        else:
            return ''

    def setSkelecog(self, flag):
        self.isSkelecog = flag

    def setExecutive(self, flag):
        wasExecutive = self.getExecutive()
        if wasExecutive:
            return
        self.isExecutive = flag
        self.updateName()
        if not wasExecutive and flag:
            self.updateHP()

    def getActualLevel(self):
        if hasattr(self, 'dna'):
            return SuitBattleGlobals.getActualFromRelativeLevel(self.getStyleName(), self.level) + 1
        else:
            self.notify.warning('called getActualLevel with no DNA, returning 1 for level')
            return 1

    def setPath(self, path):
        self.path = path
        self.pathLength = self.path.getNumPoints()

    def updateName(self):
        nameInfo = TTLocalizer.SuitBaseNameWithLevel % {'name': self._name,
                                                        'dept': self.getStyleDept(),
                                                        'level': self.getActualLevel(),
                                                        'exe': self.getExecutiveTitle(),
                                                        'revives': ''}
        self.setDisplayName(nameInfo)

    def updateHP(self):
        attributes = SuitBattleGlobals.SuitAttributes[self.dna.name]
        self.maxHP = attributes['hp'][self.level] + int(math.ceil(attributes['hp'][self.level] * SuitBattleGlobals.EXE_HP_MOD * self.getExecutive()))
        self.currHP = self.maxHP

    def getPath(self):
        return self.path

    def printPath(self):
        print '%d points in path' % self.pathLength
        for currPathPt in xrange(self.pathLength):
            indexVal = self.path.getPointIndex(currPathPt)
            print '\t', self.sp.dnaStore.getSuitPointWithIndex(indexVal)

    def makeLegList(self):
        self.legList = SuitLegList(self.path, self.sp.dnaStore, self.sp.suitWalkSpeed, SuitTimings.fromSky, SuitTimings.toSky, SuitTimings.fromSuitBuilding, SuitTimings.toSuitBuilding, SuitTimings.toToonBuilding)

    def addStatus(self, statusString):
        status = SuitBattleGlobals.getStatusFromString(statusString)
        if not status['name'] in self.statuses.keys():
            self.notify.info("Cog's status updated: " + status['name'])
            self.statuses[status['name']] = status

    def getStatus(self, name):
        if name in self.statuses.keys():
            return self.statuses[name]
        else:
            return None

    def removeStatus(self, name):
        if name in self.statuses.keys():
            lostStatus = copy.deepcopy(self.statuses.pop(name, None))
            messenger.send('suit-lost-status', [self, lostStatus])
            return lostStatus

    def decStatusRounds(self, statusName):
        for status in self.statuses.values():
            if status['name'] == statusName and 'rounds' in status:
                status['rounds'] -= 1
                if status['rounds'] <= 0:
                    self.notify.debug('%s %s has ended! (value: %d)' %
                                      (self.dna.name, status['name'], status['rounds']))
                    return self.removeStatus(status['name'])
        return None
