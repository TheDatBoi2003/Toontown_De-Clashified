from otp.ai.AIBaseGlobal import *
from otp.avatar import DistributedAvatarAI
import SuitPlannerBase, SuitBase, SuitDNA
from direct.directnotify import DirectNotifyGlobal
from toontown.battle import SuitBattleGlobals


class DistributedSuitBaseAI(DistributedAvatarAI.DistributedAvatarAI, SuitBase.SuitBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedSuitBaseAI')

    def __init__(self, air, suitPlanner):
        DistributedAvatarAI.DistributedAvatarAI.__init__(self, air)
        SuitBase.SuitBase.__init__(self)
        self.sp = suitPlanner
        self.maxHP = 10
        self.currHP = 10
        self.zoneId = 0
        self.dna = None
        self.virtual = 0
        self.skeleRevives = 0
        self.maxSkeleRevives = 0
        self.reviveFlag = 0
        self.buildingHeight = None
        return

    def generate(self):
        DistributedAvatarAI.DistributedAvatarAI.generate(self)

    def delete(self):
        self.sp = None
        del self.dna
        DistributedAvatarAI.DistributedAvatarAI.delete(self)
        return

    def requestRemoval(self):
        if self.sp:
            self.sp.removeSuit(self)
        else:
            self.requestDelete()
        return

    def setLevel(self, lvl=None):
        attributes = SuitBattleGlobals.SuitAttributes[self.dna.name]
        if lvl:
            self.level = lvl - attributes['level'] - 1
        else:
            self.level = SuitBattleGlobals.pickFromFreqList(attributes['freq'])
        self.notify.debug('Assigning level ' + str(lvl))
        if hasattr(self, 'doId'):
            self.d_setLevelDist(self.level)
        hp = attributes['hp'][self.level]
        self.maxHP = hp
        self.currHP = hp

    def getLevelDist(self):
        return self.getLevel()

    def d_setLevelDist(self, level):
        self.sendUpdate('setLevelDist', [level])

    def setupSuitDNA(self, level, track, executiveStatus=0, suitName='', hqZone=0):
        dna = SuitDNA.SuitDNA()
        name, skelecog = self.air.suitInvasionManager.getInvadingCog()
        if name is None and suitName is not '':
            name = suitName
        if name:
            dna.newSuit(name)
            attributes = SuitBattleGlobals.SuitAttributes[name]
            if attributes['level'] + 1 > level:
                level = attributes['level'] + 1
            elif attributes['level'] + len(attributes['hp']) < level:
                level = attributes['level'] + len(attributes['hp'])
        else:
            if hqZone:
                maxTier = 6
            else:
                maxTier = 5
            dna.newSuitRandom(level, track, maxTier)
        self.dna = dna
        self.track = track
        self.setLevel(level)
        self.setSkelecog(skelecog)
        self.setExecutive(executiveStatus)
        return None

    def getDNAString(self):
        if self.dna:
            return self.dna.makeNetString()
        else:
            self.notify.debug('No dna has been created for suit %d!' % self.getDoId())
            return ''

    def b_setBrushOff(self, index):
        self.setBrushOff(index)
        self.d_setBrushOff(index)
        return None

    def d_setBrushOff(self, index):
        self.sendUpdate('setBrushOff', [index])

    def setBrushOff(self, index):
        pass

    def d_denyBattle(self, toonId):
        self.sendUpdateToAvatarId(toonId, 'denyBattle', [])

    def b_setSkeleRevives(self, num):
        if num is None:
            num = 0
        self.setSkeleRevives(num)
        self.d_setSkeleRevives(self.getSkeleRevives())
        return

    def d_setSkeleRevives(self, num):
        self.sendUpdate('setSkeleRevives', [num])

    def getSkeleRevives(self):
        return self.skeleRevives

    def setSkeleRevives(self, num):
        if num is None:
            num = 0
        self.skeleRevives = num
        if num > self.maxSkeleRevives:
            self.maxSkeleRevives = num
        return

    def getMaxSkeleRevives(self):
        return self.maxSkeleRevives

    def useSkeleRevive(self):
        self.skeleRevives -= 1
        self.currHP = self.maxHP
        self.reviveFlag = 1

    def reviveCheckAndClear(self):
        returnValue = 0
        if self.reviveFlag == 1:
            returnValue = 1
            self.reviveFlag = 0
        return returnValue

    def getHP(self):
        return self.currHP

    def setHP(self, hp):
        if hp > self.maxHP * self.hardMaxHP:
            self.currHP = self.maxHP * self.hardMaxHP
        else:
            self.currHP = hp
        return None

    def b_setHP(self, hp):
        self.setHP(hp)
        self.d_setHP(hp)

    def d_setHP(self, hp):
        self.sendUpdate('setHP', [hp])

    def getStatus(self, name):
        return SuitBase.SuitBase.getStatus(self, name)

    def addStatus(self, status):
        if not status['name'] in self.statuses.keys():
            self.notify.info("Cog's status updated: " + status['name'])
            self.statuses[status['name']] = status

    def b_addStatus(self, status):
        self.addStatus(status)
        self.d_addStatus(status)

    def d_addStatus(self, status):
        statusString = SuitBattleGlobals.makeStatusString(status)
        self.sendUpdate('addStatus', [statusString])

    def removeStatus(self, name):
        return SuitBase.SuitBase.removeStatus(self, name)

    def b_removeStatus(self, name):
        self.removeStatus(name)
        self.d_removeStatus(name)

    def d_removeStatus(self, name):
        self.sendUpdate('removeStatus', [name])

    def releaseControl(self):
        return None

    def getDeathEvent(self):
        return 'cogDead-%s' % self.doId

    def resume(self):
        self.notify.debug('resume, hp=%s' % self.currHP)
        if self.currHP <= 0:
            messenger.send(self.getDeathEvent())
            self.requestRemoval()
        return None

    def prepareToJoinBattle(self):
        pass

    def b_setSkelecog(self, flag):
        self.setSkelecog(flag)
        self.d_setSkelecog(flag)

    def setSkelecog(self, flag):
        SuitBase.SuitBase.setSkelecog(self, flag)

    def d_setSkelecog(self, flag):
        self.sendUpdate('setSkelecog', [flag])

    def b_setExecutive(self, flag):
        self.setExecutive(flag)
        self.d_setExecutive(flag)

    def setExecutive(self, flag):
        wasExecutive = self.getExecutive()
        if wasExecutive:
            return

        self.isExecutive = flag

        if not wasExecutive and flag:
            self.notify.debug('Promoting ' + str(self.dna.name) + ' to exe')
            self.maxHP = self.maxHP + (self.maxHP * SuitBattleGlobals.EXE_HP_MOD * flag)
            self.currHP = self.maxHP

    def getExecutive(self):
        return self.isExecutive

    def d_setExecutive(self, flag):
        self.sendUpdate('setExecutive', [flag])

    def isForeman(self):
        return 0

    def isSupervisor(self):
        return 0

    def isClerk(self):
        return 0

    def isPresident(self):
        return 0

    def setVirtual(self, virtual):
        pass

    def getVirtual(self):
        return 0

    def isVirtual(self):
        return self.getVirtual()
