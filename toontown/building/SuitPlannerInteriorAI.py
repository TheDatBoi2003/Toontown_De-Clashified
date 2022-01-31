from otp.ai.AIBaseGlobal import *
import random

from toontown.battle import SuitBattleGlobals
from toontown.suit import SuitDNA
from direct.directnotify import DirectNotifyGlobal
from toontown.suit import DistributedSuitAI
import SuitBuildingGlobals, types

class SuitPlannerInteriorAI:
    notify = DirectNotifyGlobal.directNotify.newCategory('SuitPlannerInteriorAI')

    def __init__(self, numFloors, bldgLevel, bldgTrack, zone, respectInvasions=1, maxLvlMod=0):
        self.dbg_nSuits1stRound = config.GetBool('n-suits-1st-round', 0)
        self.dbg_4SuitsPerFloor = config.GetBool('4-suits-per-floor', 0)
        self.dbg_1SuitPerFloor = config.GetBool('1-suit-per-floor', 0)
        self.zoneId = zone
        self.numFloors = numFloors
        self.respectInvasions = respectInvasions
        dbg_defaultSuitName = simbase.config.GetString('suit-type', 'random')
        if dbg_defaultSuitName == 'random':
            self.dbg_defaultSuitType = None
        else:
            self.dbg_defaultSuitType = SuitDNA.getSuitType(dbg_defaultSuitName)
        if isinstance(bldgLevel, types.StringType):
            self.notify.warning('bldgLevel is a string!')
            bldgLevel = int(bldgLevel)
        self._genSuitInfos(numFloors, bldgLevel, bldgTrack, maxLvlMod)
        return

    def __genJoinChances(self, num):
        joinChances = []
        for currChance in xrange(num):
            joinChances.append(random.randint(1, 100))

        joinChances.sort(cmp)
        return joinChances

    def _genSuitInfos(self, numFloors, bldgLevel, bldgTrack, maxLvlMod=0, maxSuits=SuitBattleGlobals.MAX_SUIT_CAPACITY):
        self.suitInfos = []
        self.bossSpot = -1
        self.notify.debug('\n\ngenerating suitsInfos with numFloors (' + str(numFloors) + ') bldgLevel (' + str(bldgLevel) + '+1) and bldgTrack (' + str(bldgTrack) + ')')
        for currFloor in xrange(numFloors):
            infoDict = {}
            lvls = self.__genLevelList(bldgLevel, currFloor, numFloors, maxLvlMod)
            activeDicts = []
            maxActive = min(maxSuits, len(lvls))
            if self.dbg_nSuits1stRound:
                numActive = min(self.dbg_nSuits1stRound, maxActive)
            else:
                numActive = random.randint(1, maxActive)
            if currFloor + 1 == numFloors and len(lvls) > 1:
                origBossSpot = len(lvls) - 1
                if numActive == 1:
                    newBossSpot = 0
                else:
                    newBossSpot = 1
                tmp = lvls[newBossSpot]
                lvls[newBossSpot] = lvls[origBossSpot]
                lvls[origBossSpot] = tmp
                self.bossSpot = newBossSpot
            bldgInfo = SuitBuildingGlobals.SuitBuildingInfo[bldgLevel]
            if len(bldgInfo) > SuitBuildingGlobals.SUIT_BLDG_INFO_REVIVES:
                revives = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_REVIVES][0]
            else:
                revives = 0
            for currActive in xrange(numActive - 1, -1, -1):
                level = lvls[currActive]
                activeDict = self.__genSuitData(level, bldgTrack)
                activeDict['revives'] = revives
                activeDicts.append(activeDict)

            infoDict['activeSuits'] = activeDicts
            reserveDicts = []
            numReserve = len(lvls) - numActive
            joinChances = self.__genJoinChances(numReserve)
            for currReserve in xrange(numReserve):
                level = lvls[currReserve + numActive]
                reserveDict = self.__genSuitData(level, bldgTrack)
                reserveDict['revives'] = revives
                reserveDict['joinChance'] = joinChances[currReserve]
                reserveDicts.append(reserveDict)

            infoDict['reserveSuits'] = reserveDicts
            self.suitInfos.append(infoDict)

    def __genSuitData(self, lvl, track):
        suitDict = { }
        suitDict['type'] = random.choice(list(SuitDNA.getSuitDataOfDeptAndLvl(track, lvl).values()))['level']
        suitDict['track'] = track
        suitDict['level'] = lvl
        return suitDict

    def __genSuitFromLevel(self, int, track):
        return 1

    def __genLevelList(self, bldgLevel, currFloor, numFloors, maxLvlMod=0):
        bldgInfo = SuitBuildingGlobals.SuitBuildingInfo[bldgLevel]
        if self.dbg_1SuitPerFloor:
            return [1]
        else:
            if self.dbg_4SuitsPerFloor:
                return [5, 6, 7, 10]
        lvlPoolRange = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_LVL_POOL]
        maxFloors = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_FLOORS][1]
        lvlPoolMults = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_LVL_POOL_MULTS]
        floorIdx = min(currFloor, maxFloors - 1)
        lvlPoolMin = lvlPoolRange[0] * lvlPoolMults[floorIdx]
        lvlPoolMax = lvlPoolRange[1] * lvlPoolMults[floorIdx]
        lvlPool = random.randint(int(lvlPoolMin), int(lvlPoolMax))
        lvlMin = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_SUIT_LVLS][0]
        lvlMax = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_SUIT_LVLS][1] + maxLvlMod
        self.notify.debug('Level Pool: ' + str(lvlPool))
        lvlList = []
        while lvlPool >= lvlMin:
            newLvl = random.randint(lvlMin, min(lvlPool, lvlMax))
            lvlList.append(newLvl)
            lvlPool -= newLvl

        if currFloor + 1 == numFloors:
            bossLvlRange = bldgInfo[SuitBuildingGlobals.SUIT_BLDG_INFO_BOSS_LVLS]
            newLvl = random.randint(bossLvlRange[0] + maxLvlMod, bossLvlRange[1] + maxLvlMod)
            lvlList.append(newLvl)
        lvlList.sort(cmp)
        self.notify.debug('LevelList: ' + repr(lvlList))
        return lvlList

    def __setupSuitInfo(self, suit, bldgTrack, suitLevel, exeChance):
        suitName, skeleton = simbase.air.suitInvasionManager.getInvadingCog()
        dna = SuitDNA.SuitDNA()
        if suitName and self.respectInvasions:
            suitData = SuitBattleGlobals.getSuitDataFromName(suitName)
            suitType = SuitDNA.getSuitType(suitName)
            bldgTrack = SuitDNA.getSuitDept(suitName)
            suitLevel = min(max(suitLevel, suitData['level']), len(suitData['hp'])-1)
            dna.newSuit(suitName)
        else:
            dna.newSuitRandom(suitLevel, bldgTrack)
            suitType = SuitDNA.getSuitType(dna.name)
        suit.dna = dna
        self.notify.debug('Creating suit type ' + suit.dna.name + ' of level ' + str(suitLevel) + ' from type ' + str(suitType) + ' and track ' + str(bldgTrack))
        suit.setLevel(suitLevel)
        suit.b_setExecutive(random.random() <= exeChance)
        return skeleton

    def __genSuitObject(self, suitZone, suitType, bldgTrack, suitLevel, exeChance, revives=0):
        newSuit = DistributedSuitAI.DistributedSuitAI(simbase.air, None)
        skel = self.__setupSuitInfo(newSuit, bldgTrack, suitLevel, exeChance)
        if skel:
            newSuit.setSkelecog(1)
        newSuit.setSkeleRevives(revives)
        newSuit.generateWithRequired(suitZone)
        newSuit.node().setName('suit-%s' % newSuit.doId)
        return newSuit

    def myPrint(self):
        self.notify.info('Generated suits for building: ')
        for currInfo in suitInfos:
            whichSuitInfo = suitInfos.index(currInfo) + 1
            self.notify.debug(' Floor ' + str(whichSuitInfo) + ' has ' + str(len(currInfo[0])) + ' active suits.')
            for currActive in xrange(len(currInfo[0])):
                self.notify.debug('  Active suit ' + str(currActive + 1) + ' is of type ' + str(currInfo[0][currActive][0]) + ' and of track ' + str(currInfo[0][currActive][1]) + ' and of level ' + str(currInfo[0][currActive][2]))

            self.notify.debug(' Floor ' + str(whichSuitInfo) + ' has ' + str(len(currInfo[1])) + ' reserve suits.')
            for currReserve in xrange(len(currInfo[1])):
                self.notify.debug('  Reserve suit ' + str(currReserve + 1) + ' is of type ' + str(currInfo[1][currReserve][0]) + ' and of track ' + str(currInfo[1][currReserve][1]) + ' and of lvel ' + str(currInfo[1][currReserve][2]) + ' and has ' + str(currInfo[1][currReserve][3]) + '% join restriction.')

    def genFloorSuits(self, floor, exeChance=SuitBuildingGlobals.BLDG_EXE_CHANCE):
        suitHandles = {}
        floorInfo = self.suitInfos[floor]
        activeSuits = []
        for activeSuitInfo in floorInfo['activeSuits']:
            suit = self.__genSuitObject(self.zoneId, activeSuitInfo['type'], activeSuitInfo['track'], activeSuitInfo['level'], exeChance, activeSuitInfo['revives'])
            activeSuits.append(suit)

        suitHandles['activeSuits'] = activeSuits
        reserveSuits = []
        for reserveSuitInfo in floorInfo['reserveSuits']:
            suit = self.__genSuitObject(self.zoneId, reserveSuitInfo['type'], reserveSuitInfo['track'], reserveSuitInfo['level'], exeChance, reserveSuitInfo['revives'])
            reserveSuits.append((suit, reserveSuitInfo['joinChance']))

        suitHandles['reserveSuits'] = reserveSuits
        return suitHandles

    def genSuits(self):
        suitHandles = []
        for floor in xrange(len(self.suitInfos)):
            floorSuitHandles = self.genFloorSuits(floor)
            suitHandles.append(floorSuitHandles)

        return suitHandles
