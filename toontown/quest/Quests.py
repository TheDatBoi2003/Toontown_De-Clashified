from otp.otpbase import OTPGlobals
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase import ToontownGlobals
from toontown.battle import SuitBattleGlobals
from toontown.coghq import CogDisguiseGlobals
from toontown.toon import NPCToons
import copy, string
from toontown.hood import ZoneUtil
from direct.directnotify import DirectNotifyGlobal
from toontown.toonbase import TTLocalizer
from direct.showbase import PythonUtil
import time, types, random

notify = DirectNotifyGlobal.directNotify.newCategory('Quests')
ItemDict = TTLocalizer.QuestsItemDict
CompleteString = TTLocalizer.QuestsCompleteString
NotChosenString = TTLocalizer.QuestsNotChosenString
DefaultGreeting = TTLocalizer.QuestsDefaultGreeting
DefaultIncomplete = TTLocalizer.QuestsDefaultIncomplete
DefaultIncompleteProgress = TTLocalizer.QuestsDefaultIncompleteProgress
DefaultIncompleteWrongNPC = TTLocalizer.QuestsDefaultIncompleteWrongNPC
DefaultComplete = TTLocalizer.QuestsDefaultComplete
DefaultLeaving = TTLocalizer.QuestsDefaultLeaving
DefaultReject = TTLocalizer.QuestsDefaultReject
DefaultTierNotDone = TTLocalizer.QuestsDefaultTierNotDone
DefaultQuest = TTLocalizer.QuestsDefaultQuest
DefaultVisitQuestDialog = TTLocalizer.QuestsDefaultVisitQuestDialog
GREETING = 0
QUEST = 1
INCOMPLETE = 2
INCOMPLETE_PROGRESS = 3
INCOMPLETE_WRONG_NPC = 4
COMPLETE = 5
LEAVING = 6
Any = 1
OBSOLETE = 'OBSOLETE'
Start = 1
Cont = 0
Anywhere = 1
NA = 2
Same = 3
AnyFish = 4
AnyCashbotSuitPart = 5
AnyLawbotSuitPart = 6
AnyBossbotSuitPart = 7
ToonTailor = 999
ToonHQ = 1000
QuestDictTierIndex = 0
QuestDictStartIndex = 1
QuestDictDescIndex = 2
QuestDictFromNpcIndex = 3
QuestDictToNpcIndex = 4
QuestDictRewardIndex = 5
QuestDictNextQuestIndex = 6
QuestDictDialogIndex = 7
VeryEasy = 100
Easy = 75
Medium = 50
Hard = 25
VeryHard = 20
TT_TIER = 0
DD_TIER = 4
DG_TIER = 7
MM_TIER = 9
BR_TIER = 12
DL_TIER = 15
FINALE_TIER = 19
ELDER_TIER = 20
LOOPING_FINAL_TIER = ELDER_TIER
VISIT_QUEST_ID = 1000
TUTORIAL_QUEST_ID = 101
TROLLEY_QUEST_ID = 102
FIRST_COG_QUEST_ID = 103
PHONE_QUEST_ID = 104
NEWBIE_HP = 25
from toontown.toonbase.ToontownGlobals import FT_FullSuit, FT_Leg, FT_Arm, FT_Torso, MaxTrainingFrames

QuestRandGen = random.Random()


def seedRandomGen(npcId, avId, tier, rewardHistory):
    QuestRandGen.seed(npcId * 100 + avId + tier + len(rewardHistory))


def seededRandomChoice(seq):
    return QuestRandGen.choice(seq)


def getCompleteStatusWithNpc(questComplete, toNpcId, npc):
    if questComplete:
        if npc:
            if npcMatches(toNpcId, npc):
                return COMPLETE
            else:
                return INCOMPLETE_WRONG_NPC
        else:
            return COMPLETE
    elif npc:
        if npcMatches(toNpcId, npc):
            return INCOMPLETE_PROGRESS
        else:
            return INCOMPLETE
    else:
        return INCOMPLETE


def npcMatches(toNpcId, npc):
    return toNpcId == npc.getNpcId() or toNpcId == Any or toNpcId == ToonHQ and npc.getHq() or toNpcId == ToonTailor and npc.getTailor()


def calcRecoverChance(numberNotDone, baseChance, cap=1):
    chance = baseChance
    avgNum2Kill = 1.0 / (chance / 100.0)
    if numberNotDone >= avgNum2Kill * 1.5 and cap:
        chance = 1000
    elif numberNotDone > avgNum2Kill * 0.5:
        diff = float(numberNotDone - avgNum2Kill * 0.5)
        luck = 1.0 + abs(diff / (avgNum2Kill * 0.5))
        chance *= luck
    return chance


def simulateRecoveryVar(numNeeded, baseChance, list=0, cap=1):
    numHave = 0
    numTries = 0
    greatestFailChain = 0
    currentFail = 0
    capHits = 0
    attemptList = {}
    while numHave < numNeeded:
        numTries += 1
        chance = calcRecoverChance(currentFail, baseChance, cap)
        test = random.random() * 100
        if chance == 1000:
            capHits += 1
        if test < chance:
            numHave += 1
            if currentFail > greatestFailChain:
                greatestFailChain = currentFail
            if attemptList.get(currentFail):
                attemptList[currentFail] += 1
            else:
                attemptList[currentFail] = 1
            currentFail = 0
        else:
            currentFail += 1

    print 'Test results: %s tries, %s longest failure chain, %s cap hits' % (numTries, greatestFailChain, capHits)
    if list:
        print 'failures for each succes %s' % attemptList


def simulateRecoveryFix(numNeeded, baseChance, list=0):
    numHave = 0
    numTries = 0
    greatestFailChain = 0
    currentFail = 0
    attemptList = {}
    while numHave < numNeeded:
        numTries += 1
        chance = baseChance
        test = random.random() * 100
        if test < chance:
            numHave += 1
            if currentFail > greatestFailChain:
                greatestFailChain = currentFail
            if attemptList.get(currentFail):
                attemptList[currentFail] += 1
            else:
                attemptList[currentFail] = 1
            currentFail = 0
        else:
            currentFail += 1

    print 'Test results: %s tries, %s longest failure chain' % (numTries, greatestFailChain)
    if list:
        print 'failures for each succes %s' % attemptList


class Quest:
    _cogTracks = [Any,
                  'c',
                  'l',
                  'm',
                  's']
    _factoryTypes = [Any,
                     FT_FullSuit,
                     FT_Leg,
                     FT_Arm,
                     FT_Torso]

    def check(self, cond, msg):
        pass

    def checkLocation(self, location):
        locations = [Anywhere] + TTLocalizer.GlobalStreetNames.keys()
        self.check(location in locations, 'invalid location: %s' % location)

    def checkNumCogs(self, num):
        self.check(1, 'invalid number of cogs: %s' % num)

    def checkNewbieLevel(self, level):
        self.check(1, 'invalid newbie level: %s' % level)

    def checkCogType(self, type):
        types = [Any] + SuitBattleGlobals.SuitAttributes.keys()
        self.check(type in types, 'invalid cog type: %s' % type)

    def checkCogTrack(self, track):
        self.check(track in self._cogTracks, 'invalid cog track: %s' % track)

    def checkCogLevel(self, level):
        self.check(level >= 1 and level <= 12, 'invalid cog level: %s' % level)

    def checkNumSkelecogs(self, num):
        self.check(1, 'invalid number of cogs: %s' % num)

    def checkSkelecogTrack(self, track):
        self.check(track in self._cogTracks, 'invalid cog track: %s' % track)

    def checkSkelecogLevel(self, level):
        self.check(level >= 1 and level <= 12, 'invalid cog level: %s' % level)

    def checkNumSkeleRevives(self, num):
        self.check(1, 'invalid number of cogs: %s' % num)

    def checkNumForemen(self, num):
        self.check(num > 0, 'invalid number of foremen: %s' % num)

    def checkNumVPs(self, num):
        self.check(num > 0, 'invalid number of VPs: %s' % num)

    def checkNumSupervisors(self, num):
        self.check(num > 0, 'invalid number of supervisors: %s' % num)

    def checkNumCFOs(self, num):
        self.check(num > 0, 'invalid number of CFOs: %s' % num)

    def checkNumClerks(self, num):
        self.check(num > 0, 'invalid number of clerks: %s' % num)

    def checkNumCJs(self, num):
        self.check(num > 0, 'invalid number of CJs: %s' % num)

    def checkNumPresidents(self, num):
        self.check(num > 0, 'invalid number of club presidents: %s' % num)

    def checkNumCEOs(self, num):
        self.check(num > 0, 'invalid number of CEOs: %s' % num)

    def checkNumBuildings(self, num):
        self.check(1, 'invalid num buildings: %s' % num)

    def checkBuildingTrack(self, track):
        self.check(track in self._cogTracks, 'invalid building track: %s' % track)

    def checkBuildingFloors(self, floors):
        self.check(floors >= 1 and floors <= 5, 'invalid num floors: %s' % floors)

    def checkNumFactories(self, num):
        self.check(1, 'invalid num factories: %s' % num)

    def checkFactoryType(self, type):
        self.check(type in self._factoryTypes, 'invalid factory type: %s' % type)

    def checkNumMints(self, num):
        self.check(1, 'invalid num mints: %s' % num)

    def checkNumStages(self, num):
        self.check(1, 'invalid num stages: %s' % num)

    def checkNumClubs(self, num):
        self.check(1, 'invalid num clubs: %s' % num)

    def checkNumCogParts(self, num):
        self.check(1, 'invalid num cog parts: %s' % num)

    def checkNumGags(self, num):
        self.check(1, 'invalid num gags: %s' % num)

    def checkGagTrack(self, track):
        self.check(track >= ToontownBattleGlobals.MIN_TRACK_INDEX and track <= ToontownBattleGlobals.MAX_TRACK_INDEX,
                   'invalid gag track: %s' % track)

    def checkGagItem(self, item):
        self.check(item >= ToontownBattleGlobals.MIN_LEVEL_INDEX and item <= ToontownBattleGlobals.MAX_LEVEL_INDEX,
                   'invalid gag item: %s' % item)

    def checkDeliveryItem(self, item):
        self.check(item in ItemDict, 'invalid delivery item: %s' % item)

    def checkNumItems(self, num):
        self.check(1, 'invalid num items: %s' % num)

    def checkRecoveryItem(self, item):
        self.check(item in ItemDict, 'invalid recovery item: %s' % item)

    def checkPercentChance(self, chance):
        self.check(chance > 0 and chance <= 100, 'invalid percent chance: %s' % chance)

    def checkRecoveryItemHolderAndType(self, holder, holderType='type'):
        holderTypes = ['type', 'level', 'track']
        self.check(holderType in holderTypes, 'invalid recovery item holderType: %s' % holderType)
        if holderType == 'type':
            holders = [Any, AnyFish] + SuitBattleGlobals.SuitAttributes.keys()
            self.check(holder in holders, 'invalid recovery item holder: %s for holderType: %s' % (holder, holderType))
        elif holderType == 'level':
            pass
        elif holderType == 'track':
            self.check(holder in self._cogTracks,
                       'invalid recovery item holder: %s for holderType: %s' % (holder, holderType))

    def checkTrackChoice(self, option):
        self.check(option >= ToontownBattleGlobals.MIN_TRACK_INDEX and option <= ToontownBattleGlobals.MAX_TRACK_INDEX,
                   'invalid track option: %s' % option)

    def checkNumFriends(self, num):
        self.check(1, 'invalid number of friends: %s' % num)

    def checkNumMinigames(self, num):
        self.check(1, 'invalid number of minigames: %s' % num)

    def filterFunc(avatar):
        return 1

    filterFunc = staticmethod(filterFunc)

    def __init__(self, id, quest):
        self.id = id
        self.quest = quest

    def getId(self):
        return self.id

    def getType(self):
        return self.__class__

    def getObjectiveStrings(self):
        return ['']

    def getString(self):
        return self.getObjectiveStrings()[0]

    def getRewardString(self, progressString):
        return self.getString() + ' : ' + progressString

    def getChooseString(self):
        return self.getString()

    def getPosterString(self):
        return self.getString()

    def getHeadlineString(self):
        return self.getString()

    def getDefaultQuestDialog(self):
        return self.getString() + TTLocalizer.Period

    def getNumQuestItems(self):
        return -1

    def addArticle(self, num, oString):
        if len(oString) == 0:
            return oString
        if num == 1:
            return oString
        else:
            return '%d %s' % (num, oString)

    def __repr__(self):
        return 'Quest type: %s id: %s params: %s' % (self.__class__.__name__, self.id, self.quest[0:])

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesVPCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesCFOCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesCJCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesCEOCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesFactoryCount(self, avId, location, avList):
        return 0

    def doesMintCount(self, avId, location, avList):
        return 0

    def doesCogPartCount(self, avId, location, avList):
        return 0

    def getCompletionStatus(self, av, questDesc, npc=None):
        notify.error('Pure virtual - please override me')
        return None


class LocationBasedQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)
        self.checkLocation(self.quest[0])

    def getLocation(self):
        return self.quest[0]

    def getLocationName(self):
        loc = self.getLocation()
        if loc == Anywhere:
            locName = ''
        elif loc in ToontownGlobals.hoodNameMap:
            locName = TTLocalizer.QuestInLocationString % {'inPhrase': ToontownGlobals.hoodNameMap[loc][1],
                                                           'location': ToontownGlobals.hoodNameMap[loc][
                                                                           -1] + TTLocalizer.QuestsLocationArticle}
        elif loc in ToontownGlobals.StreetBranchZones:
            locName = TTLocalizer.QuestInLocationString % {'inPhrase': ToontownGlobals.StreetNames[loc][1],
                                                           'location': ToontownGlobals.StreetNames[loc][
                                                                           -1] + TTLocalizer.QuestsLocationArticle}
        return locName

    def isLocationMatch(self, zoneId):
        loc = self.getLocation()
        if loc is Anywhere:
            return 1
        if ZoneUtil.isPlayground(loc):
            if loc == ZoneUtil.getCanonicalHoodId(zoneId):
                return 1
            else:
                return 0
        elif loc == ZoneUtil.getCanonicalBranchZone(zoneId):
            return 1
        elif loc == zoneId:
            return 1
        else:
            return 0

    def getChooseString(self):
        return TTLocalizer.QuestsLocationString % {'string': self.getString(),
                                                   'location': self.getLocationName()}

    def getPosterString(self):
        return TTLocalizer.QuestsLocationString % {'string': self.getString(),
                                                   'location': self.getLocationName()}

    def getDefaultQuestDialog(self):
        return (TTLocalizer.QuestsLocationString + TTLocalizer.Period) % {'string': self.getString(),
                                                                          'location': self.getLocationName()}


class CogQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        if self.__class__ == CogQuest:
            self.checkNumCogs(self.quest[1])
            self.checkCogType(self.quest[2])

    def getCogType(self):
        return self.quest[2]

    def getNumQuestItems(self):
        return self.getNumCogs()

    def getNumCogs(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumCogs()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumCogs() == 1:
            return ''
        else:
            return TTLocalizer.QuestsCogQuestProgress % {'progress': questDesc[4],
                                                         'numCogs': self.getNumCogs()}

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        cogType = self.getCogType()
        if numCogs == 1:
            if cogType == Any:
                return TTLocalizer.Cog
            else:
                return SuitBattleGlobals.SuitAttributes[cogType]['singularName']
        elif cogType == Any:
            return TTLocalizer.Cogs
        else:
            return SuitBattleGlobals.SuitAttributes[cogType]['pluralName']

    def getObjectiveStrings(self):
        cogName = self.getCogNameString()
        numCogs = self.getNumCogs()
        if numCogs == 1:
            text = cogName
        else:
            text = TTLocalizer.QuestsCogQuestDefeatDesc % {'numCogs': numCogs,
                                                           'cogName': cogName}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsCogQuestDefeat % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumCogs():
            return getFinishToonTaskSCStrings(toNpcId)
        cogName = self.getCogNameString()
        numCogs = self.getNumCogs()
        if numCogs == 1:
            text = TTLocalizer.QuestsCogQuestSCStringS
        else:
            text = TTLocalizer.QuestsCogQuestSCStringP
        cogLoc = self.getLocationName()
        return text % {'cogName': cogName,
                       'cogLoc': cogLoc}

    def getHeadlineString(self):
        return TTLocalizer.QuestsCogQuestHeadline

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        questCogType = self.getCogType()
        return (questCogType is Any or questCogType is cogDict['type']) and avId in cogDict[
            'activeToons'] and self.isLocationMatch(zoneId)

    def getNewbieLevel(self):
        return self.quest[3]


class CogTrackQuest(CogQuest):
    trackCodes = ['c',
                  'l',
                  'm',
                  's']
    trackNamesS = [TTLocalizer.BossbotS,
                   TTLocalizer.LawbotS,
                   TTLocalizer.CashbotS,
                   TTLocalizer.SellbotS]
    trackNamesP = [TTLocalizer.BossbotP,
                   TTLocalizer.LawbotP,
                   TTLocalizer.CashbotP,
                   TTLocalizer.SellbotP]

    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        if self.__class__ == CogTrackQuest:
            self.checkNumCogs(self.quest[1])
            self.checkCogTrack(self.quest[2])

    def getCogTrack(self):
        return self.quest[2]

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumCogs() == 1:
            return ''
        else:
            return TTLocalizer.QuestsCogTrackQuestProgress % {'progress': questDesc[4],
                                                              'numCogs': self.getNumCogs()}

    def getObjectiveStrings(self):
        numCogs = self.getNumCogs()
        track = self.trackCodes.index(self.getCogTrack())
        if numCogs == 1:
            text = self.trackNamesS[track]
        else:
            text = TTLocalizer.QuestsCogTrackDefeatDesc % {'numCogs': numCogs,
                                                           'trackName': self.trackNamesP[track]}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsCogTrackQuestDefeat % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumCogs():
            return getFinishToonTaskSCStrings(toNpcId)
        numCogs = self.getNumCogs()
        track = self.trackCodes.index(self.getCogTrack())
        if numCogs == 1:
            cogText = self.trackNamesS[track]
            text = TTLocalizer.QuestsCogTrackQuestSCStringS
        else:
            cogText = self.trackNamesP[track]
            text = TTLocalizer.QuestsCogTrackQuestSCStringP
        cogLocName = self.getLocationName()
        return text % {'cogText': cogText,
                       'cogLoc': cogLocName}

    def getHeadlineString(self):
        return TTLocalizer.QuestsCogTrackQuestHeadline

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        questCogTrack = self.getCogTrack()
        return questCogTrack == cogDict['track'] and avId in cogDict['activeToons'] and self.isLocationMatch(zoneId)


class CogLevelQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumCogs(self.quest[1])
        self.checkCogLevel(self.quest[2])

    def getCogType(self):
        return Any

    def getCogLevel(self):
        return self.quest[2]

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumCogs() == 1:
            return ''
        else:
            return TTLocalizer.QuestsCogLevelQuestProgress % {'progress': questDesc[4],
                                                              'numCogs': self.getNumCogs()}

    def getObjectiveStrings(self):
        count = self.getNumCogs()
        level = self.getCogLevel()
        name = self.getCogNameString()
        if count == 1:
            text = TTLocalizer.QuestsCogLevelQuestDesc
        else:
            text = TTLocalizer.QuestsCogLevelQuestDescC
        return (text % {'count': count,
                        'level': level,
                        'name': name},)

    def getString(self):
        return TTLocalizer.QuestsCogLevelQuestDefeat % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumCogs():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumCogs()
        level = self.getCogLevel()
        name = self.getCogNameString()
        if count == 1:
            text = TTLocalizer.QuestsCogLevelQuestDesc
        else:
            text = TTLocalizer.QuestsCogLevelQuestDescI
        objective = text % {'level': level,
                            'name': name}
        location = self.getLocationName()
        return TTLocalizer.QuestsCogLevelQuestSCString % {'objective': objective,
                                                          'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsCogLevelQuestHeadline

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        questCogLevel = self.getCogLevel()
        return questCogLevel <= cogDict['level'] and avId in cogDict['activeToons'] and self.isLocationMatch(zoneId)


class SkelecogQBase:
    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ASkeleton
        else:
            return TTLocalizer.SkeletonP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['isSkelecog'] and avId in cogDict['activeToons'] and self.isLocationMatch(zoneId)


class SkelecogQuest(CogQuest, SkelecogQBase):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumSkelecogs(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        return SkelecogQBase.getCogNameString(self)

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return SkelecogQBase.doesCogCount(self, avId, cogDict, zoneId, avList)


class SkelecogTrackQuest(CogTrackQuest, SkelecogQBase):
    trackNamesS = [TTLocalizer.BossbotSkelS,
                   TTLocalizer.LawbotSkelS,
                   TTLocalizer.CashbotSkelS,
                   TTLocalizer.SellbotSkelS]
    trackNamesP = [TTLocalizer.BossbotSkelP,
                   TTLocalizer.LawbotSkelP,
                   TTLocalizer.CashbotSkelP,
                   TTLocalizer.SellbotSkelP]

    def __init__(self, id, quest):
        CogTrackQuest.__init__(self, id, quest)
        self.checkNumSkelecogs(self.quest[1])
        self.checkSkelecogTrack(self.quest[2])

    def getCogNameString(self):
        return SkelecogQBase.getCogNameString(self)

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return SkelecogQBase.doesCogCount(self, avId, cogDict, zoneId, avList) and self.getCogTrack() == cogDict[
            'track']


class SkelecogLevelQuest(CogLevelQuest, SkelecogQBase):
    def __init__(self, id, quest):
        CogLevelQuest.__init__(self, id, quest)
        self.checkNumSkelecogs(self.quest[1])
        self.checkSkelecogLevel(self.quest[2])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        return SkelecogQBase.getCogNameString(self)

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return SkelecogQBase.doesCogCount(self, avId, cogDict, zoneId, avList) and self.getCogLevel() <= cogDict[
            'level']


class SkeleReviveQBase:
    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.Av2Cog
        else:
            return TTLocalizer.v2CogP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['hasRevives'] and avId in cogDict['activeToons'] and self.isLocationMatch(zoneId)


class SkeleReviveQuest(CogQuest, SkeleReviveQBase):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumSkeleRevives(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        return SkeleReviveQBase.getCogNameString(self)

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return SkeleReviveQBase.doesCogCount(self, avId, cogDict, zoneId, avList)


class ForemanQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumForemen(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.AForeman
        else:
            return TTLocalizer.ForemanP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return bool(CogQuest.doesCogCount(self, avId, cogDict, zoneId, avList) and cogDict['isForeman'])


class VPQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumVPs(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ACogVP
        else:
            return TTLocalizer.CogVPs

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['isBoss'] > 0 and self.isLocationMatch(zoneId)

    def doesCFOCount(self, avId, cogDict, zoneId, avList):
        return self.doesCogCount(avId, cogDict, zoneId, avList)


class SupervisorQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumSupervisors(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ASupervisor
        else:
            return TTLocalizer.SupervisorP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return bool(CogQuest.doesCogCount(self, avId, cogDict, zoneId, avList) and cogDict['isSupervisor'])


class CFOQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumCFOs(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ACogCFO
        else:
            return TTLocalizer.CogCFOs

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['isBoss'] > 0 and self.isLocationMatch(zoneId)

    def doesVPCount(self, avId, cogDict, zoneId, avList):
        return self.doesCogCount(avId, cogDict, zoneId, avList)


class ClerkQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumClerks(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.AClerk
        else:
            return TTLocalizer.ClerkP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return bool(CogQuest.doesCogCount(self, avId, cogDict, zoneId, avList) and cogDict['isClerk'])


class CJQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumCJs(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ACogCJ
        else:
            return TTLocalizer.CogCJs

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['isBoss'] > 0 and self.isLocationMatch(zoneId)

    def doesCFOCount(self, avId, cogDict, zoneId, avList):
        return self.doesCogCount(avId, cogDict, zoneId, avList)


class PresidentQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumPresidents(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.AClubPresident
        else:
            return TTLocalizer.ClubPresidentP

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return bool(CogQuest.doesCogCount(self, avId, cogDict, zoneId, avList) and cogDict['isPresident'])


class CEOQuest(CogQuest):
    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumCEOs(self.quest[1])

    def getCogType(self):
        return Any

    def getCogNameString(self):
        numCogs = self.getNumCogs()
        if numCogs == 1:
            return TTLocalizer.ACogCEO
        else:
            return TTLocalizer.CogCEOs

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return cogDict['isBoss'] > 0 and self.isLocationMatch(zoneId)

    def doesCFOCount(self, avId, cogDict, zoneId, avList):
        return self.doesCogCount(avId, cogDict, zoneId, avList)


class RescueQuest(VPQuest):
    def __init__(self, id, quest):
        VPQuest.__init__(self, id, quest)

    def getNumToons(self):
        return self.getNumCogs()

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumToons() == 1:
            return ''
        else:
            return TTLocalizer.QuestsRescueQuestProgress % {'progress': questDesc[4],
                                                            'numToons': self.getNumToons()}

    def getObjectiveStrings(self):
        numToons = self.getNumCogs()
        if numToons == 1:
            text = TTLocalizer.QuestsRescueQuestToonS
        else:
            text = TTLocalizer.QuestsRescueQuestRescueDesc % {'numToons': numToons}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsRescueQuestRescue % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumToons():
            return getFinishToonTaskSCStrings(toNpcId)
        numToons = self.getNumToons()
        if numToons == 1:
            text = TTLocalizer.QuestsRescueQuestSCStringS
        else:
            text = TTLocalizer.QuestsRescueQuestSCStringP
        toonLoc = self.getLocationName()
        return text % {'toonLoc': toonLoc}

    def getHeadlineString(self):
        return TTLocalizer.QuestsRescueQuestHeadline


class BuildingQuest(CogQuest):
    trackCodes = ['c',
                  'l',
                  'm',
                  's']
    trackNames = [TTLocalizer.Bossbot,
                  TTLocalizer.Lawbot,
                  TTLocalizer.Cashbot,
                  TTLocalizer.Sellbot]

    def __init__(self, id, quest):
        CogQuest.__init__(self, id, quest)
        self.checkNumBuildings(self.quest[1])
        self.checkBuildingTrack(self.quest[2])
        self.checkBuildingFloors(self.quest[3])

    def getNumFloors(self):
        return self.quest[3]

    def getBuildingTrack(self):
        return self.quest[2]

    def getNumQuestItems(self):
        return self.getNumBuildings()

    def getNumBuildings(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumBuildings()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumBuildings() == 1:
            return ''
        else:
            return TTLocalizer.QuestsBuildingQuestProgressString % {'progress': questDesc[4],
                                                                    'num': self.getNumBuildings()}

    def getObjectiveStrings(self):
        count = self.getNumBuildings()
        floors = TTLocalizer.QuestsBuildingQuestFloorNumbers[self.getNumFloors() - 1]
        buildingTrack = self.getBuildingTrack()
        if buildingTrack == Any:
            type = TTLocalizer.Cog
        else:
            type = self.trackNames[self.trackCodes.index(buildingTrack)]
        if count == 1:
            if floors == '':
                text = TTLocalizer.QuestsBuildingQuestDesc
            else:
                text = TTLocalizer.QuestsBuildingQuestDescF
        elif floors == '':
            text = TTLocalizer.QuestsBuildingQuestDescC
        else:
            text = TTLocalizer.QuestsBuildingQuestDescCF
        return (text % {'count': count,
                        'floors': floors,
                        'type': type},)

    def getString(self):
        return TTLocalizer.QuestsBuildingQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumBuildings():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumBuildings()
        floors = TTLocalizer.QuestsBuildingQuestFloorNumbers[self.getNumFloors() - 1]
        buildingTrack = self.getBuildingTrack()
        if buildingTrack == Any:
            type = TTLocalizer.Cog
        else:
            type = self.trackNames[self.trackCodes.index(buildingTrack)]
        if count == 1:
            if floors == '':
                text = TTLocalizer.QuestsBuildingQuestDesc
            else:
                text = TTLocalizer.QuestsBuildingQuestDescF
        elif floors == '':
            text = TTLocalizer.QuestsBuildingQuestDescI
        else:
            text = TTLocalizer.QuestsBuildingQuestDescIF
        objective = text % {'floors': floors,
                            'type': type}
        location = self.getLocationName()
        return TTLocalizer.QuestsBuildingQuestSCString % {'objective': objective,
                                                          'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsBuildingQuestHeadline

    def doesCogCount(self, avId, cogDict, zoneId, avList):
        return 0

    def doesBuildingCount(self, avId, avList):
        return 1


class FactoryQuest(LocationBasedQuest):
    factoryTypeNames = {FT_FullSuit: TTLocalizer.Cog,
                        FT_Leg: TTLocalizer.FactoryTypeLeg,
                        FT_Arm: TTLocalizer.FactoryTypeArm,
                        FT_Torso: TTLocalizer.FactoryTypeTorso}

    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumFactories(self.quest[1])

    def getNumQuestItems(self):
        return self.getNumFactories()

    def getNumFactories(self):
        return self.quest[1]

    def getFactoryType(self):
        loc = self.getLocation()
        type = Any
        if loc in ToontownGlobals.facilityIdToType:
            type = ToontownGlobals.facilityIdToType[loc]
        return type

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumFactories()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumFactories() == 1:
            return ''
        else:
            return TTLocalizer.QuestsFactoryQuestProgressString % {'progress': questDesc[4],
                                                                   'num': self.getNumFactories()}

    def getObjectiveStrings(self):
        count = self.getNumFactories()
        factoryType = self.getFactoryType()
        if factoryType == Any:
            type = TTLocalizer.Cog
        else:
            type = FactoryQuest.factoryTypeNames[factoryType]
        if count == 1:
            text = TTLocalizer.QuestsFactoryQuestDesc
        else:
            text = TTLocalizer.QuestsFactoryQuestDescC
        return (text % {'count': count,
                        'type': type},)

    def getString(self):
        return TTLocalizer.QuestsFactoryQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumFactories():
            return getFinishToonTaskSCStrings(toNpcId)
        factoryType = self.getFactoryType()
        if factoryType == Any:
            type = TTLocalizer.Cog
        else:
            type = FactoryQuest.factoryTypeNames[factoryType]
        count = self.getNumFactories()
        if count == 1:
            text = TTLocalizer.QuestsFactoryQuestDesc
        else:
            text = TTLocalizer.QuestsFactoryQuestDescI
        objective = text % {'type': type}
        location = self.getLocationName()
        return TTLocalizer.QuestsFactoryQuestSCString % {'objective': objective,
                                                         'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsFactoryQuestHeadline

    def doesFactoryCount(self, avId, location, avList):
        return self.isLocationMatch(location)


class MintQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumMints(self.quest[1])

    def getNumQuestItems(self):
        return self.getNumMints()

    def getNumMints(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumMints()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumMints() == 1:
            return ''
        else:
            return TTLocalizer.QuestsMintQuestProgressString % {'progress': questDesc[4],
                                                                'num': self.getNumMints()}

    def getObjectiveStrings(self):
        count = self.getNumMints()
        if count == 1:
            text = TTLocalizer.QuestsMintQuestDesc
        else:
            text = TTLocalizer.QuestsMintQuestDescC % {'count': count}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsMintQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumMints():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumMints()
        if count == 1:
            objective = TTLocalizer.QuestsMintQuestDesc
        else:
            objective = TTLocalizer.QuestsMintQuestDescI
        location = self.getLocationName()
        return TTLocalizer.QuestsMintQuestSCString % {'objective': objective,
                                                      'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsMintQuestHeadline

    def doesMintCount(self, avId, location, avList):
        return self.isLocationMatch(location)


class StageQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumStages(self.quest[1])

    def getNumQuestItems(self):
        return self.getNumStages()

    def getNumStages(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumStages()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumStages() == 1:
            return ''
        else:
            return TTLocalizer.QuestsMintQuestProgressString % {'progress': questDesc[4],
                                                                'num': self.getNumStages()}

    def getObjectiveStrings(self):
        count = self.getNumStages()
        if count == 1:
            text = TTLocalizer.QuestsStageQuestDesc
        else:
            text = TTLocalizer.QuestsStageQuestDescC % {'count': count}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsMintQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumStages():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumStages()
        if count == 1:
            objective = TTLocalizer.QuestsStageQuestDesc
        else:
            objective = TTLocalizer.QuestsStageQuestDescI
        location = self.getLocationName()
        return TTLocalizer.QuestsMintQuestSCString % {'objective': objective,
                                                      'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsMintQuestHeadline

    def doesMintCount(self, avId, location, avList):
        return self.isLocationMatch(location)


class ClubQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumClubs(self.quest[1])

    def getNumQuestItems(self):
        return self.getNumClubs()

    def getNumClubs(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumClubs()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumClubs() == 1:
            return ''
        else:
            return TTLocalizer.QuestsCountryClubQuestProgressString % {'progress': questDesc[4],
                                                                       'num': self.getNumClubs()}

    def getObjectiveStrings(self):
        count = self.getNumClubs()
        if count == 1:
            text = TTLocalizer.QuestsCountryClubQuestDesc
        else:
            text = TTLocalizer.QuestsCountryClubQuestDescC % {'count': count}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsCountryClubQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumClubs():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumClubs()
        if count == 1:
            objective = TTLocalizer.QuestsCountryClubQuestDesc
        else:
            objective = TTLocalizer.QuestsCountryClubQuestDescI
        location = self.getLocationName()
        return TTLocalizer.QuestsCountryClubQuestSCString % {'objective': objective,
                                                             'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsCountryClubQuestHeadline

    def doesMintCount(self, avId, location, avList):
        return self.isLocationMatch(location)


class CogPartQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumCogParts(self.quest[1])

    def getNumQuestItems(self):
        return self.getNumParts()

    def getNumParts(self):
        return self.quest[1]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= self.getNumParts()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumParts() == 1:
            return ''
        else:
            return TTLocalizer.QuestsCogPartQuestProgressString % {'progress': questDesc[4],
                                                                   'num': self.getNumParts()}

    def getObjectiveStrings(self):
        count = self.getNumParts()
        if count == 1:
            text = TTLocalizer.QuestsCogPartQuestDesc
        else:
            text = TTLocalizer.QuestsCogPartQuestDescC
        return (text % {'count': count},)

    def getString(self):
        return TTLocalizer.QuestsCogPartQuestString % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumParts():
            return getFinishToonTaskSCStrings(toNpcId)
        count = self.getNumParts()
        if count == 1:
            text = TTLocalizer.QuestsCogPartQuestDesc
        else:
            text = TTLocalizer.QuestsCogPartQuestDescI
        objective = text
        location = self.getLocationName()
        return TTLocalizer.QuestsCogPartQuestSCString % {'objective': objective,
                                                         'location': location}

    def getHeadlineString(self):
        return TTLocalizer.QuestsCogPartQuestHeadline

    def doesCogPartCount(self, avId, location, avList):
        return self.isLocationMatch(location)


class DeliverGagQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)
        self.checkNumGags(self.quest[0])
        self.checkGagTrack(self.quest[1])
        self.checkGagItem(self.quest[2])

    def getGagType(self):
        return self.quest[1]

    def getNumQuestItems(self):
        return self.getNumGags()

    def getNumGags(self):
        return self.quest[0]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        gagLevel = self.getGagType()
        num = self.getNumGags()
        questComplete = npc and av.inventory and av.inventory.numItemLevel(gagLevel) >= num
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumGags() == 1:
            return ''
        else:
            return TTLocalizer.QuestsDeliverGagQuestProgress % {'progress': questDesc[4],
                                                                'numGags': self.getNumGags()}

    def getObjectiveStrings(self):
        track, item = self.getGagType()
        num = self.getNumGags()
        if num == 1:
            text = ToontownBattleGlobals.AvPropStringsSingular[track][item]
        else:
            gagName = ToontownBattleGlobals.AvPropStringsPlural[track][item]
            text = TTLocalizer.QuestsItemNameAndNum % {'num': TTLocalizer.getLocalNum(num),
                                                       'name': gagName}
        return (text,)

    def getString(self):
        return TTLocalizer.QuestsDeliverGagQuestString % self.getObjectiveStrings()[0]

    def getRewardString(self, progress):
        return TTLocalizer.QuestsDeliverGagQuestStringLong % self.getObjectiveStrings()[0]

    def getDefaultQuestDialog(self):
        return TTLocalizer.QuestsDeliverGagQuestStringLong % self.getObjectiveStrings()[
            0] + '\x07' + TTLocalizer.QuestsDeliverGagQuestInstructions

    def getSCStrings(self, toNpcId, progress):
        if progress >= self.getNumGags():
            return getFinishToonTaskSCStrings(toNpcId)
        track, item = self.getGagType()
        num = self.getNumGags()
        if num == 1:
            text = TTLocalizer.QuestsDeliverGagQuestToSCStringS
            gagName = ToontownBattleGlobals.AvPropStringsSingular[track][item]
        else:
            text = TTLocalizer.QuestsDeliverGagQuestToSCStringP
            gagName = ToontownBattleGlobals.AvPropStringsPlural[track][item]
        return [text % {'gagName': gagName}, TTLocalizer.QuestsDeliverGagQuestSCString] + getVisitSCStrings(toNpcId)

    def getHeadlineString(self):
        return TTLocalizer.QuestsDeliverGagQuestHeadline


class DeliverItemQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)
        self.checkDeliveryItem(self.quest[0])

    def getItem(self):
        return self.quest[0]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        if npc and npcMatches(toNpcId, npc):
            return COMPLETE
        else:
            return INCOMPLETE_WRONG_NPC

    def getProgressString(self, avatar, questDesc):
        return TTLocalizer.QuestsDeliverItemQuestProgress

    def getObjectiveStrings(self):
        iDict = ItemDict[self.getItem()]
        article = iDict[2]
        itemName = iDict[0]
        return [article + itemName]

    def getString(self):
        return TTLocalizer.QuestsDeliverItemQuestString % self.getObjectiveStrings()[0]

    def getRewardString(self, progress):
        return TTLocalizer.QuestsDeliverItemQuestStringLong % self.getObjectiveStrings()[0]

    def getDefaultQuestDialog(self):
        return TTLocalizer.QuestsDeliverItemQuestStringLong % self.getObjectiveStrings()[0]

    def getSCStrings(self, toNpcId, progress):
        iDict = ItemDict[self.getItem()]
        article = iDict[2]
        itemName = iDict[0]
        return [TTLocalizer.QuestsDeliverItemQuestSCString % {'article': article,
                                                              'itemName': itemName}] + getVisitSCStrings(toNpcId)

    def getHeadlineString(self):
        return TTLocalizer.QuestsDeliverItemQuestHeadline


class VisitQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        if npc and npcMatches(toNpcId, npc):
            return COMPLETE
        else:
            return INCOMPLETE_WRONG_NPC

    def getProgressString(self, avatar, questDesc):
        return TTLocalizer.QuestsVisitQuestProgress

    def getObjectiveStrings(self):
        return ['']

    def getString(self):
        return TTLocalizer.QuestsVisitQuestStringShort

    def getChooseString(self):
        return TTLocalizer.QuestsVisitQuestStringLong

    def getRewardString(self, progress):
        return TTLocalizer.QuestsVisitQuestStringLong

    def getDefaultQuestDialog(self):
        return random.choice(DefaultVisitQuestDialog)

    def getSCStrings(self, toNpcId, progress):
        return getVisitSCStrings(toNpcId)

    def getHeadlineString(self):
        return TTLocalizer.QuestsVisitQuestHeadline


class RecoverItemQuest(LocationBasedQuest):
    def __init__(self, id, quest):
        LocationBasedQuest.__init__(self, id, quest)
        self.checkNumItems(self.quest[1])
        self.checkRecoveryItem(self.quest[2])
        self.checkPercentChance(self.quest[3])
        if len(self.quest) > 5:
            self.checkRecoveryItemHolderAndType(self.quest[4], self.quest[5])
        else:
            self.checkRecoveryItemHolderAndType(self.quest[4])

    def testRecover(self, progress):
        test = random.random() * 100
        chance = self.getPercentChance()
        numberDone = progress & pow(2, 16) - 1
        numberNotDone = progress >> 16
        returnTest = None
        avgNum2Kill = 1.0 / (chance / 100.0)
        if numberNotDone >= avgNum2Kill * 1.5:
            chance = 100
        elif numberNotDone > avgNum2Kill * 0.5:
            diff = float(numberNotDone - avgNum2Kill * 0.5)
            luck = 1.0 + abs(diff / (avgNum2Kill * 0.5))
            chance *= luck
        if test <= chance:
            returnTest = 1
            numberNotDone = 0
            numberDone += 1
        else:
            returnTest = 0
            numberNotDone += 1
            numberDone += 0
        returnCount = numberNotDone << 16
        returnCount += numberDone
        return returnTest, returnCount

    def testDone(self, progress):
        numberDone = progress & pow(2, 16) - 1
        print 'Quest number done %s' % numberDone
        if numberDone >= self.getNumItems():
            return 1
        else:
            return 0

    def getNumQuestItems(self):
        return self.getNumItems()

    def getNumItems(self):
        return self.quest[1]

    def getItem(self):
        return self.quest[2]

    def getPercentChance(self):
        return self.quest[3]

    def getHolder(self):
        return self.quest[4]

    def getHolderType(self):
        if len(self.quest) == 5:
            return 'type'
        else:
            return self.quest[5]

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        forwardProgress = toonProgress & pow(2, 16) - 1
        questComplete = forwardProgress >= self.getNumItems()
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        elif self.getNumItems() == 1:
            return ''
        else:
            progress = questDesc[4] & pow(2, 16) - 1
            return TTLocalizer.QuestsRecoverItemQuestProgress % {'progress': progress,
                                                                 'numItems': self.getNumItems()}

    def getObjectiveStrings(self):
        holder = self.getHolder()
        holderType = self.getHolderType()
        if holder == Any:
            holderName = TTLocalizer.TheCogs
        elif holder == AnyFish:
            holderName = TTLocalizer.AFish
        elif holderType == 'type':
            holderName = SuitBattleGlobals.SuitAttributes[holder]['pluralName']
        elif holderType == 'level':
            holderName = TTLocalizer.QuestsRecoverItemQuestHolderString % {'level': TTLocalizer.Level,
                                                                           'holder': holder,
                                                                           'cogs': TTLocalizer.Cogs}
        elif holderType == 'track':
            if holder == 'c':
                holderName = TTLocalizer.BossbotP
            elif holder == 's':
                holderName = TTLocalizer.SellbotP
            elif holder == 'm':
                holderName = TTLocalizer.CashbotP
            elif holder == 'l':
                holderName = TTLocalizer.LawbotP
        item = self.getItem()
        num = self.getNumItems()
        if num == 1:
            itemName = ItemDict[item][2] + ItemDict[item][0]
        else:
            itemName = TTLocalizer.QuestsItemNameAndNum % {'num': TTLocalizer.getLocalNum(num),
                                                           'name': ItemDict[item][1]}
        return [itemName, holderName]

    def getString(self):
        return TTLocalizer.QuestsRecoverItemQuestString % {'item': self.getObjectiveStrings()[0],
                                                           'holder': self.getObjectiveStrings()[1]}

    def getSCStrings(self, toNpcId, progress):
        item = self.getItem()
        num = self.getNumItems()
        forwardProgress = progress & pow(2, 16) - 1
        if forwardProgress >= self.getNumItems():
            if num == 1:
                itemName = ItemDict[item][2] + ItemDict[item][0]
            else:
                itemName = TTLocalizer.QuestsItemNameAndNum % {'num': TTLocalizer.getLocalNum(num),
                                                               'name': ItemDict[item][1]}
            if toNpcId == ToonHQ:
                strings = [TTLocalizer.QuestsRecoverItemQuestReturnToHQSCString % itemName,
                           TTLocalizer.QuestsRecoverItemQuestGoToHQSCString]
            elif toNpcId:
                npcName, hoodName, buildingArticle, buildingName, toStreet, streetName, isInPlayground = getNpcInfo(
                    toNpcId)
                strings = [TTLocalizer.QuestsRecoverItemQuestReturnToSCString % {'item': itemName,
                                                                                 'npcName': npcName}]
                if isInPlayground:
                    strings.append(TTLocalizer.QuestsRecoverItemQuestGoToPlaygroundSCString % hoodName)
                else:
                    strings.append(TTLocalizer.QuestsRecoverItemQuestGoToStreetSCString % {'to': toStreet,
                                                                                           'street': streetName,
                                                                                           'hood': hoodName})
                strings.extend(
                    [TTLocalizer.QuestsRecoverItemQuestVisitBuildingSCString % (buildingArticle, buildingName),
                     TTLocalizer.QuestsRecoverItemQuestWhereIsBuildingSCString % (buildingArticle, buildingName)])
            return strings
        holder = self.getHolder()
        holderType = self.getHolderType()
        locName = self.getLocationName()
        if holder == Any:
            holderName = TTLocalizer.TheCogs
        elif holder == AnyFish:
            holderName = TTLocalizer.TheFish
        elif holderType == 'type':
            holderName = SuitBattleGlobals.SuitAttributes[holder]['pluralName']
        elif holderType == 'level':
            holderName = TTLocalizer.QuestsRecoverItemQuestHolderString % {'level': TTLocalizer.Level,
                                                                           'holder': holder,
                                                                           'cogs': TTLocalizer.Cogs}
        elif holderType == 'track':
            if holder == 'c':
                holderName = TTLocalizer.BossbotP
            elif holder == 's':
                holderName = TTLocalizer.SellbotP
            elif holder == 'm':
                holderName = TTLocalizer.CashbotP
            elif holder == 'l':
                holderName = TTLocalizer.LawbotP
        if num == 1:
            itemName = ItemDict[item][2] + ItemDict[item][0]
        else:
            itemName = TTLocalizer.QuestsItemNameAndNum % {'num': TTLocalizer.getLocalNum(num),
                                                           'name': ItemDict[item][1]}
        return TTLocalizer.QuestsRecoverItemQuestRecoverFromSCString % {'item': itemName,
                                                                        'holder': holderName,
                                                                        'loc': locName}

    def getHeadlineString(self):
        return TTLocalizer.QuestsRecoverItemQuestHeadline


class FriendQuest(Quest):
    def filterFunc(avatar):
        if len(avatar.getFriendsList()) == 0:
            return 1
        else:
            return 0

    filterFunc = staticmethod(filterFunc)

    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= 1 or len(av.getFriendsList()) > 0
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        else:
            return ''

    def getString(self):
        return TTLocalizer.QuestsFriendQuestString

    def getSCStrings(self, toNpcId, progress):
        if progress:
            return getFinishToonTaskSCStrings(toNpcId)
        return TTLocalizer.QuestsFriendQuestSCString

    def getHeadlineString(self):
        return TTLocalizer.QuestsFriendQuestHeadline

    def getObjectiveStrings(self):
        return [TTLocalizer.QuestsFriendQuestString]

    def doesFriendCount(self, av, otherAv):
        return 1


class TrolleyQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= 1
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        else:
            return ''

    def getString(self):
        return TTLocalizer.QuestsFriendQuestString

    def getSCStrings(self, toNpcId, progress):
        if progress:
            return getFinishToonTaskSCStrings(toNpcId)
        return TTLocalizer.QuestsTrolleyQuestSCString

    def getHeadlineString(self):
        return TTLocalizer.QuestsTrolleyQuestHeadline

    def getObjectiveStrings(self):
        return [TTLocalizer.QuestsTrolleyQuestString]


class MailboxQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= 1
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        else:
            return ''

    def getString(self):
        return TTLocalizer.QuestsMailboxQuestString

    def getSCStrings(self, toNpcId, progress):
        if progress:
            return getFinishToonTaskSCStrings(toNpcId)
        return TTLocalizer.QuestsMailboxQuestSCString

    def getHeadlineString(self):
        return TTLocalizer.QuestsMailboxQuestHeadline

    def getObjectiveStrings(self):
        return [TTLocalizer.QuestsMailboxQuestString]


class PhoneQuest(Quest):
    def __init__(self, id, quest):
        Quest.__init__(self, id, quest)

    def getCompletionStatus(self, av, questDesc, npc=None):
        questId, fromNpcId, toNpcId, rewardId, toonProgress = questDesc
        questComplete = toonProgress >= 1
        return getCompleteStatusWithNpc(questComplete, toNpcId, npc)

    def getProgressString(self, avatar, questDesc):
        if self.getCompletionStatus(avatar, questDesc) == COMPLETE:
            return CompleteString
        else:
            return ''

    def getString(self):
        return TTLocalizer.QuestsPhoneQuestString

    def getSCStrings(self, toNpcId, progress):
        if progress:
            return getFinishToonTaskSCStrings(toNpcId)
        return TTLocalizer.QuestsPhoneQuestSCString

    def getHeadlineString(self):
        return TTLocalizer.QuestsPhoneQuestHeadline

    def getObjectiveStrings(self):
        return [TTLocalizer.QuestsPhoneQuestString]


DefaultDialog = {GREETING: DefaultGreeting,
                 QUEST: DefaultQuest,
                 INCOMPLETE: DefaultIncomplete,
                 INCOMPLETE_PROGRESS: DefaultIncompleteProgress,
                 INCOMPLETE_WRONG_NPC: DefaultIncompleteWrongNPC,
                 COMPLETE: DefaultComplete,
                 LEAVING: DefaultLeaving}


def getQuestFromNpcId(id):
    return QuestDict.get(id)[QuestDictFromNpcIndex]


def getQuestToNpcId(id):
    return QuestDict.get(id)[QuestDictToNpcIndex]


def getQuestDialog(id):
    return QuestDict.get(id)[QuestDictDialogIndex]


def getQuestReward(id, av):
    baseRewardId = QuestDict.get(id)[QuestDictRewardIndex]
    return baseRewardId


def isQuestJustForFun(questId, rewardId):
    questEntry = QuestDict.get(questId)
    if questEntry:
        tier = questEntry[QuestDictTierIndex]
        return isRewardOptional(tier, rewardId)
    else:
        return False


PreCatalogQuestIds = [TUTORIAL_QUEST_ID, TROLLEY_QUEST_ID, FIRST_COG_QUEST_ID]
NoRewardTierZeroQuests = PreCatalogQuestIds + [PHONE_QUEST_ID]
RewardTierZeroQuests = []
TierZeroQuests = NoRewardTierZeroQuests + RewardTierZeroQuests
QuestDict = {
    # Quest ID : ( tier, start, (questDesc), fromNpc, toNpc, reward, nextQuest, dialog )
    # some quests have 'OBSOLETE' for their reward; this is for obsolete quests
    # that some users might still be working on; the 'OBSOLETE' prevents the
    # quest from being assigned to users in the future

    # This is the tutorial quest
    TUTORIAL_QUEST_ID: (TT_TIER, Start, (VisitQuest,), Any, 2001, NA, TROLLEY_QUEST_ID, DefaultDialog),

    # This is the trolley quest, tutorial toons will have to complete this before they leave the playground
    TROLLEY_QUEST_ID: (TT_TIER, Cont, (TrolleyQuest,), Any, ToonHQ, NA, FIRST_COG_QUEST_ID, DefaultDialog),

    # This is the first combat task, toons can  now go to the streets
    FIRST_COG_QUEST_ID: (TT_TIER, Cont,
                         (RecoverItemQuest, ToontownGlobals.ToontownCentral, 1, 20, VeryEasy, Any, 'type'),
                         ToonHQ, ToonHQ, NA, PHONE_QUEST_ID, DefaultDialog),

    # First catalog will be delivered here
    # Also, final tutorial quest
    PHONE_QUEST_ID: (TT_TIER, Cont, (PhoneQuest,), Same, ToonHQ, 100, NA, TTLocalizer.QuestDialogDict[PHONE_QUEST_ID]),

    # 105-119 are available

    # visiting quest 1000 is special
    # VISIT_QUEST_ID : ( 1, 1, (VisitQuest,), Any, Any, NA, NA, DefaultDialog),

    # Training frames quest
    120: (TT_TIER + 1, Start, (VisitQuest,), Any, 2001, NA, 121,
          TTLocalizer.QuestDialogDict[120]),
    121: (TT_TIER + 1, Start, (CogQuest, Anywhere, 4, Any), 2001, Same, NA, (122, 123, 124, 125),
          TTLocalizer.QuestDialogDict[121]),
    122: (TT_TIER + 1, Cont, (CogTrackQuest, Anywhere, 4, 'c'), Same, Same, NA, (126, 127, 128),
          TTLocalizer.QuestDialogDict[122]),
    123: (TT_TIER + 1, Cont, (CogTrackQuest, Anywhere, 4, 'l'), Same, Same, NA, (126, 127, 128),
          TTLocalizer.QuestDialogDict[123]),
    124: (TT_TIER + 1, Cont, (CogTrackQuest, Anywhere, 4, 's'), Same, Same, NA, (126, 127, 128),
          TTLocalizer.QuestDialogDict[124]),
    125: (TT_TIER + 1, Cont, (CogTrackQuest, Anywhere, 4, 'm'), Same, Same, NA, (126, 127, 128),
          TTLocalizer.QuestDialogDict[125]),
    126: (TT_TIER + 1, Cont, (VisitQuest,), Same, 2005, NA, 400, TTLocalizer.QuestDialogDict[126]),
    127: (TT_TIER + 1, Cont, (VisitQuest,), Same, 2311, NA, 400, TTLocalizer.QuestDialogDict[127]),
    128: (TT_TIER + 1, Cont, (VisitQuest,), Same, 2119, NA, 400, TTLocalizer.QuestDialogDict[128]),
    400: (TT_TIER + 1, Cont, (VisitQuest,), Same, 2001, 801, NA, TTLocalizer.QuestDialogDict[400]),

    # Toontown central
    1001: (
        TT_TIER + 2, Start, (CogQuest, ToontownGlobals.ToontownCentral, 3, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    1002: (
        TT_TIER + 2, Start, (CogQuest, ToontownGlobals.ToontownCentral, 4, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    1003: (
        TT_TIER + 2, Start, (CogQuest, ToontownGlobals.ToontownCentral, 5, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    1004: (
        TT_TIER + 2, Start, (CogQuest, ToontownGlobals.ToontownCentral, 6, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    1005: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'f'), Any, ToonHQ, Any, NA, DefaultDialog),
    1006: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'p'), Any, ToonHQ, Any, NA, DefaultDialog),
    1007: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    1008: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    1009: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'sc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1010: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'pp'), Any, ToonHQ, Any, NA, DefaultDialog),
    1011: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1012: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),

    1013: (TT_TIER + 2, Start, (CogQuest, Anywhere, 3, 'f'), Any, ToonHQ, Any, NA, DefaultDialog),
    1014: (TT_TIER + 2, Start, (CogQuest, Anywhere, 3, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    1015: (TT_TIER + 2, Start, (CogQuest, Anywhere, 3, 'sc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1016: (TT_TIER + 2, Start, (CogQuest, Anywhere, 3, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),

    1017: (TT_TIER + 2, Start, (CogQuest, Anywhere, 1, 'ym'), Any, ToonHQ, Any, NA, DefaultDialog),
    1018: (TT_TIER + 2, Start, (CogQuest, Anywhere, 1, 'nd'), Any, ToonHQ, Any, NA, DefaultDialog),
    1019: (TT_TIER + 2, Start, (CogQuest, Anywhere, 1, 'tw'), Any, ToonHQ, Any, NA, DefaultDialog),
    1020: (TT_TIER + 2, Start, (CogQuest, Anywhere, 1, 'dt'), Any, ToonHQ, Any, NA, DefaultDialog),

    1021: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 2, 2), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1022: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 6, 2), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1023: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 3, 2), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1024: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 4, 2), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1025: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 4, 3), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1026: (
        TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 6, 3), Any, ToonHQ, Any, NA,
        DefaultDialog),

    1027: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 2, 'm'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1028: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 2, 's'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1029: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 2, 'c'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1030: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 2, 'l'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1031: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 3, 'm'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1032: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 3, 's'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1033: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 3, 'c'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1034: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 3, 'l'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1035: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 5, 'm'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1036: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 5, 's'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1037: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 5, 'c'), Any, ToonHQ, Any, NA,
        DefaultDialog),
    1038: (
        TT_TIER + 2, Start, (CogTrackQuest, ToontownGlobals.ToontownCentral, 5, 'l'), Any, ToonHQ, Any, NA,
        DefaultDialog),

    # Next are NPC Quests. More random quests for TTC are found after 1100.

    # Help out Loopy Lane.  For a reward, you get teleport access to TTC.
    1039: (TT_TIER + 3, Start, (VisitQuest,), Any, 2135, NA, (1041, 1042, 1043),
           TTLocalizer.QuestDialogDict[1039]),
    1040: (TT_TIER + 3, Start, (VisitQuest,), Any, 2207, NA, (1041, 1042, 1043),
           TTLocalizer.QuestDialogDict[1040]),
    1041: (TT_TIER + 3, Cont, (VisitQuest,), Same, 2211, NA, 1044,
           TTLocalizer.QuestDialogDict[1041]),
    1042: (TT_TIER + 3, Cont, (VisitQuest,), Same, 2209, NA, 1044,
           TTLocalizer.QuestDialogDict[1042]),
    1043: (TT_TIER + 3, Cont, (VisitQuest,), Same, 2210, NA, 1044,
           TTLocalizer.QuestDialogDict[1043]),
    1044: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 4, 7, VeryEasy, Any, 'type'), Same, Same, NA, 1045,
           TTLocalizer.QuestDialogDict[1044]),
    1045: (TT_TIER + 3, Cont, (DeliverItemQuest, 8), Same, ToonHQ, 300, NA,
           TTLocalizer.QuestDialogDict[1045]),

    # Funny Money needs to recover their adding machines.  Reward is +2 HP.
    1046: (TT_TIER + 3, Start, (VisitQuest,), Any, 2127, NA, 1047,
           TTLocalizer.QuestDialogDict[1046]),
    1047: (TT_TIER + 3, Start, (RecoverItemQuest, Anywhere, 3, 9, VeryEasy, 'm', 'track'), 2127, Same, NA, 1048,
           TTLocalizer.QuestDialogDict[1047]),
    1048: (TT_TIER + 3, Cont, (DeliverItemQuest, 9), Same, 2131, NA, 1049,
           TTLocalizer.QuestDialogDict[1048]),
    1049: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 3, 2007, VeryEasy, 'c', 'track'), Same, Same, NA, 1053,
           TTLocalizer.QuestDialogDict[1049]),
    1053: (TT_TIER + 3, Cont, (DeliverItemQuest, 9), Same, 2127, 101, NA,
           TTLocalizer.QuestDialogDict[1053]),

    # Used Clown Cars needs to recover tires.  Your reward is the medium pouch
    # so you can now carry 25 gags.
    1054: (TT_TIER + 1, Start, (VisitQuest,), Any, 2128, NA, 1055,
           TTLocalizer.QuestDialogDict[1054]),
    1055: (TT_TIER + 1, Start, (RecoverItemQuest, Anywhere, 4, 10, Easy, AnyFish), 2128, Same, NA, 1056,
           TTLocalizer.QuestDialogDict[1055]),
    1056: (TT_TIER + 1, Cont, (VisitQuest,), Same, 2213, NA, 1057,
           TTLocalizer.QuestDialogDict[1056]),
    1057: (TT_TIER + 1, Cont, (CogLevelQuest, ToontownGlobals.ToontownCentral, 6, 3), Same, Same, NA, 1058,
           TTLocalizer.QuestDialogDict[1057]),
    1058: (TT_TIER + 1, Cont, (DeliverItemQuest, 11), Same, 2128, 200, NA,
           TTLocalizer.QuestDialogDict[1058]),

    # Ink shortage.  Reward is +2 HP.
    1059: (TT_TIER + 3, Start, (VisitQuest,), Any, 2302, NA, 1060,
           TTLocalizer.QuestDialogDict[1059]),
    1060: (TT_TIER + 3, Start, (RecoverItemQuest, Anywhere, 1, 12, Medium, AnyFish), 2302, Same, NA, 1062,
           TTLocalizer.QuestDialogDict[1060]),
    1061: (TT_TIER + 3, Cont, (CogQuest, ToontownGlobals.ToontownCentral, 6, 'p'), Same, Same, 101, NA,
           TTLocalizer.QuestDialogDict[1061]),
    1062: (TT_TIER + 3, Cont, (CogQuest, ToontownGlobals.ToontownCentral, 6, 'b'), Same, Same, 101, NA,
           TTLocalizer.QuestDialogDict[1062]),

    # Two packages for Dr. ???  Reward is track frame #2.
    900: (TT_TIER + 3, Start, (VisitQuest,), Any, 2201, NA, 1063,
          TTLocalizer.QuestDialogDict[900]),
    1063: (TT_TIER + 3, Start, (RecoverItemQuest, Anywhere, 1, 13, Easy, 3, 'level'), 2201, Same, NA, 1067,
           TTLocalizer.QuestDialogDict[1063]),
    1067: (TT_TIER + 3, Cont, (DeliverItemQuest, 13), Same, 2112, NA, 1068,
           TTLocalizer.QuestDialogDict[1067]),
    1068: (TT_TIER + 3, Cont, (CogQuest, ToontownGlobals.SillyStreet, 5, Any), Same, Same, NA, (1069, 1070, 1071),
           TTLocalizer.QuestDialogDict[1068]),
    1069: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 13, Easy, 'm', 'track'), Same, Same, NA, 1072,
           TTLocalizer.QuestDialogDict[1069]),
    1070: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 13, Easy, 's', 'track'), Same, Same, NA, 1072,
           TTLocalizer.QuestDialogDict[1070]),
    1071: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 13, Easy, 'c', 'track'), Same, Same, NA, 1072,
           TTLocalizer.QuestDialogDict[1071]),
    1072: (TT_TIER + 3, Cont, (DeliverItemQuest, 13), Same, 2301, NA, 1073,
           TTLocalizer.QuestDialogDict[1072]),
    1073: (TT_TIER + 3, Cont, (VisitQuest,), Any, 2201, NA, 1074,
           TTLocalizer.QuestDialogDict[1073]),
    1074: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 13, Medium, Any), Same, Same, NA, 1075,
           TTLocalizer.QuestDialogDict[1074]),
    1075: (TT_TIER + 3, Cont, (DeliverItemQuest, 13), Same, 2301, 802, NA,
           TTLocalizer.QuestDialogDict[1075]),

    # 14K Goldfish.  Reward is max quest = 2.
    1076: (TT_TIER + 2, Start, (VisitQuest,), Any, 2217, NA, 1077,
           TTLocalizer.QuestDialogDict[1076]),
    1077: (TT_TIER + 2, Start, (RecoverItemQuest, Anywhere, 1, 14, Medium, Any), 2217, Same, NA, 1078,
           TTLocalizer.QuestDialogDict[1077]),
    1078: (TT_TIER + 2, Cont, (DeliverItemQuest, 14), Same, 2302, NA, 1079,
           TTLocalizer.QuestDialogDict[1078]),
    1079: (TT_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 15, Easy, 'f'), Same, 2217, NA, 1080,
           TTLocalizer.QuestDialogDict[1079]),
    1092: (TT_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 15, Easy, 'sc'), Same, 2217, NA, 1080,
           TTLocalizer.QuestDialogDict[1092]),
    1080: (TT_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 4, 15, Easy, AnyFish), Same, Same, 500, NA,
           TTLocalizer.QuestDialogDict[1080]),

    # Sticky Lou glued to floor.  Reward is +3 HP.
    1081: (TT_TIER + 3, Start, (VisitQuest,), Any, 2208, NA, 1082,
           TTLocalizer.QuestDialogDict[1081]),
    1082: (TT_TIER + 3, Start, (RecoverItemQuest, Anywhere, 1, 16, Medium, 's', 'track'), 2208, Same, NA, 1083,
           TTLocalizer.QuestDialogDict[1082]),
    1083: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 17, Medium, 'l', 'track'), Same, Same, NA, 1084,
           TTLocalizer.QuestDialogDict[1083]),
    1084: (TT_TIER + 3, Cont, (RecoverItemQuest, Anywhere, 1, 18, Medium, 'm', 'track'), Same, Same, 102, NA,
           TTLocalizer.QuestDialogDict[1084]),

    # Professor Pete is analyzing Cogs.  Get him some gears and your reward
    # is +1 HP.
    1085: (TT_TIER + 2, Start, (VisitQuest,), Any, 2003, NA, 1086,
           TTLocalizer.QuestDialogDict[1085]),
    1086: (TT_TIER + 2, Start, (RecoverItemQuest, Anywhere, 5, 2007, Easy, 2, 'level'), 2003, Same, NA, 1089,
           TTLocalizer.QuestDialogDict[1086]),
    1089: (TT_TIER + 2, Cont, (DeliverItemQuest, 19), Same, ToonHQ, 100, NA,
           TTLocalizer.QuestDialogDict[1089]),

    # Learn about Cog Radar.  Kill Cogs.  Gain +2 HP. 
    1090: (TT_TIER + 2, Start, (VisitQuest,), Any, 2119, NA, 1091,
           TTLocalizer.QuestDialogDict[1090]),
    1091: (TT_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 8, 2), 2119, ToonHQ, 101, NA,
           TTLocalizer.QuestDialogDict[1091]),

    # More random quests for TT_TIER+2
    1105: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'f'), Any, ToonHQ, Any, NA, DefaultDialog),
    1106: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'p'), Any, ToonHQ, Any, NA, DefaultDialog),
    1107: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    1108: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    1109: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'sc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1110: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'pp'), Any, ToonHQ, Any, NA, DefaultDialog),
    1111: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1112: (TT_TIER + 2, Start, (CogQuest, Anywhere, 2, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),

    # More random quests for TT_TIER+3 # for trailers stuck on last gag track quest
    1205: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'f'), Any, ToonHQ, Any, NA, DefaultDialog),
    1206: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'p'), Any, ToonHQ, Any, NA, DefaultDialog),
    1207: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    1208: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    1209: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'sc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1210: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'pp'), Any, ToonHQ, Any, NA, DefaultDialog),
    1211: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),
    1212: (TT_TIER + 3, Start, (CogQuest, Anywhere, 4, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),

    # Professor Pete wants you to defeat some cogs before you leave.  Reward: carry 30 gags
    1300: (TT_TIER + 3, Start, (VisitQuest,), Any, 2003, NA, 1301, TTLocalizer.QuestDialogDict[1300]),
    1301: (TT_TIER + 3, Start, (CogLevelQuest, ToontownGlobals.ToontownCentral, 5, 4), 2003, Same, NA, 1302,
           TTLocalizer.QuestDialogDict[1301]),
    1302: (TT_TIER + 3, Cont, (DeliverItemQuest, 1300), Same, ToonHQ, NA, 1303, TTLocalizer.QuestDialogDict[1302]),
    1303: (TT_TIER + 3, Cont, (DeliverItemQuest, 1301), Same, 2003, 201, NA, TTLocalizer.QuestDialogDict[1303]),

    # Donald's Dock
    1400: (DD_TIER, Start, (VisitQuest,), Any, 1328, NA, 1401, TTLocalizer.QuestDialogDict[1400]),
    1401: (DD_TIER, Start, (RecoverItemQuest, ToontownGlobals.BuccaneerBoulevard, 1, 1401, Easy, 'p'), 1328, Same, 400, NA,
           TTLocalizer.QuestDialogDict[1401]),

    # Optional quests to do while working on the bottleneck quest
    2001: (DD_TIER, Start, (CogQuest, Anywhere, 3, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2002: (DD_TIER, Start, (CogQuest, Anywhere, 4, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2003: (DD_TIER, Start, (CogQuest, Anywhere, 5, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2004: (DD_TIER, Start, (CogQuest, Anywhere, 6, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2005: (DD_TIER, Start, (CogQuest, Anywhere, 7, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2006: (DD_TIER, Start, (CogQuest, Anywhere, 8, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2007: (DD_TIER, Start, (CogQuest, Anywhere, 9, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2008: (DD_TIER, Start, (CogQuest, Anywhere, 10, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2009: (DD_TIER, Start, (CogQuest, Anywhere, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2010: (DD_TIER, Start, (CogLevelQuest, Anywhere, 2, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2011: (DD_TIER, Start, (CogLevelQuest, Anywhere, 3, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2012: (DD_TIER, Start, (CogLevelQuest, Anywhere, 2, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2013: (DD_TIER, Start, (CogLevelQuest, Anywhere, 4, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2014: (DD_TIER, Start, (CogLevelQuest, Anywhere, 4, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2015: (DD_TIER, Start, (CogLevelQuest, Anywhere, 5, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2816: (DD_TIER, Start, (CogLevelQuest, Anywhere, 4, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2817: (DD_TIER, Start, (CogLevelQuest, Anywhere, 5, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2818: (DD_TIER, Start, (CogLevelQuest, Anywhere, 6, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2819: (DD_TIER, Start, (CogLevelQuest, Anywhere, 7, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    # DD is heavy on low-level corporate (bossbot) cogs (levels 2-4)
    # and also medium-level money (cashbot) cogs (levels 3-6).  It's
    # light on legal and sales cogs.

    2101: (DD_TIER + 1, Start, (CogQuest, ToontownGlobals.DonaldsDock, 3, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2102: (DD_TIER + 1, Start, (CogQuest, ToontownGlobals.DonaldsDock, 4, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2103: (DD_TIER + 1, Start, (CogQuest, ToontownGlobals.DonaldsDock, 5, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2104: (DD_TIER + 1, Start, (CogQuest, Anywhere, 6, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2105: (DD_TIER + 1, Start, (CogQuest, Anywhere, 7, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2106: (DD_TIER + 1, Start, (CogQuest, Anywhere, 8, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    2107: (DD_TIER + 1, Start, (CogQuest, Anywhere, 6, 'f'), Any, ToonHQ, Any, NA, DefaultDialog),
    2108: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'p'), Any, ToonHQ, Any, NA, DefaultDialog),
    2109: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'ym'), Any, ToonHQ, Any, NA, DefaultDialog),
    2110: (DD_TIER + 1, Start, (CogQuest, Anywhere, 3, 'mm'), Any, ToonHQ, Any, NA, DefaultDialog),
    2111: (DD_TIER + 1, Start, (CogQuest, Anywhere, 2, 'ds'), Any, ToonHQ, Any, NA, DefaultDialog),
    2112: (DD_TIER + 1, Start, (CogQuest, Anywhere, 1, 'hh'), Any, ToonHQ, Any, NA, DefaultDialog),

    2113: (DD_TIER + 1, Start, (CogQuest, Anywhere, 6, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),
    2114: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),
    2115: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'nd'), Any, ToonHQ, Any, NA, DefaultDialog),
    2116: (DD_TIER + 1, Start, (CogQuest, Anywhere, 3, 'gh'), Any, ToonHQ, Any, NA, DefaultDialog),
    2117: (DD_TIER + 1, Start, (CogQuest, Anywhere, 2, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),
    2118: (DD_TIER + 1, Start, (CogQuest, Anywhere, 1, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),

    2119: (DD_TIER + 1, Start, (CogQuest, Anywhere, 6, 'sc'), Any, ToonHQ, Any, NA, DefaultDialog),
    2120: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'pp'), Any, ToonHQ, Any, NA, DefaultDialog),
    2121: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'tw'), Any, ToonHQ, Any, NA, DefaultDialog),
    2122: (DD_TIER + 1, Start, (CogQuest, Anywhere, 3, 'bc'), Any, ToonHQ, Any, NA, DefaultDialog),
    2123: (DD_TIER + 1, Start, (CogQuest, Anywhere, 2, 'nc'), Any, ToonHQ, Any, NA, DefaultDialog),
    2124: (DD_TIER + 1, Start, (CogQuest, Anywhere, 1, 'mb'), Any, ToonHQ, Any, NA, DefaultDialog),

    2125: (DD_TIER + 1, Start, (CogQuest, Anywhere, 6, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    2126: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    2127: (DD_TIER + 1, Start, (CogQuest, Anywhere, 4, 'dt'), Any, ToonHQ, Any, NA, DefaultDialog),
    2128: (DD_TIER + 1, Start, (CogQuest, Anywhere, 3, 'ac'), Any, ToonHQ, Any, NA, DefaultDialog),
    2129: (DD_TIER + 1, Start, (CogQuest, Anywhere, 2, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),
    2130: (DD_TIER + 1, Start, (CogQuest, Anywhere, 1, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),

    2131: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 2, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2132: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 3, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2133: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 2, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2134: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 4, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2135: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 4, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2136: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 5, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2137: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 4, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2138: (DD_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.DonaldsDock, 6, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    2139: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 3, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    2140: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 3, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    2141: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 3, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    2142: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 3, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    2143: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 5, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    2144: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 5, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    2145: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 5, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    2146: (
        DD_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.DonaldsDock, 5, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    2147: (DD_TIER + 1, Start, (CogTrackQuest, Anywhere, 7, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    2148: (DD_TIER + 1, Start, (CogTrackQuest, Anywhere, 7, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    2149: (DD_TIER + 1, Start, (CogTrackQuest, Anywhere, 7, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    2150: (DD_TIER + 1, Start, (CogTrackQuest, Anywhere, 7, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    2151: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, Any, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    2152: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    2153: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    2154: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    2155: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'm', 1), Any, ToonHQ, Any, NA, DefaultDialog),
    2156: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 's', 1), Any, ToonHQ, Any, NA, DefaultDialog),
    2157: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'c', 1), Any, ToonHQ, Any, NA, DefaultDialog),
    2158: (DD_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'l', 1), Any, ToonHQ, Any, NA, DefaultDialog),

    2159: (DD_TIER + 1, Start, (DeliverGagQuest, 3, 1), Any, Any, Any, NA, DefaultDialog),
    2160: (DD_TIER + 1, Start, (DeliverGagQuest, 2, 1), Any, Any, Any, NA, DefaultDialog),
    2161: (DD_TIER + 1, Start, (DeliverGagQuest, 1, 2), Any, Any, Any, NA, DefaultDialog),
    2162: (DD_TIER + 1, Start, (DeliverGagQuest, 2, 2), Any, Any, Any, NA, DefaultDialog),

    # Billy Budd at the Barnacle Barn has lost an inner tube.  He
    # thinks a Penny Pincher stole it.  Reward: +2 Laff.
    2201: (DD_TIER + 1, Start, (VisitQuest,), Any, 1101, NA, 2202,
           TTLocalizer.QuestDialogDict[2201]),
    2202: (DD_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 2001, Medium, 'pp'), 1101, Same, 101, NA,
           TTLocalizer.QuestDialogDict[2202]),

    # Captain Carl needs you to take his eyeglass prescription to the Doctor Queequeg.
    # Doctor Queequeg in turn needs you to recover eyeglass frames from a flunky.
    # When you deliver the frames to Dr. Q he will fill the prescription and give
    # the toon the glasses to return to Captain Carl. Reward: carry 35 gags
    2203: (DD_TIER + 1, Start, (VisitQuest,), Any, 1102, NA, 2204,
           TTLocalizer.QuestDialogDict[2203]),
    2204: (DD_TIER + 1, Start, (DeliverItemQuest, 2002), 1102, 1104, NA, 2205,
           TTLocalizer.QuestDialogDict[2204]),
    2205: (DD_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 2003, Medium, 'f'), Same, Same, NA, 2206,
           TTLocalizer.QuestDialogDict[2205]),
    2206: (DD_TIER + 1, Cont, (DeliverItemQuest, 2004), Same, 1102, 202, NA,
           TTLocalizer.QuestDialogDict[2206]),

    # Barnacle Barbara at the Barnacle Barn has lost her big white wig.  She
    # says a back stabber stole it.  Reward: +1 Laff
    2207: (DD_TIER + 1, Start, (VisitQuest,), Any, 1201, NA, 2208,
           TTLocalizer.QuestDialogDict[2207]),
    2208: (DD_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 2005, Easy, 'bs'), 1201, Same, 100, NA,
           TTLocalizer.QuestDialogDict[2208]),

    # Melville needs some things for his cog fighting sailing voyage. First go see Alice and
    # do what she asks to get some ballast. Then go see Art and do what he asks to get a
    # sailing chart. Reward: teleport access
    2209: (DD_TIER + 2, Start, (VisitQuest,), Any, 1302, NA, 2210,
           TTLocalizer.QuestDialogDict[2209]),
    2210: (DD_TIER + 2, Start, (VisitQuest,), 1302, 1301, NA, 2211,
           TTLocalizer.QuestDialogDict[2210]),
    2211: (DD_TIER + 2, Cont, (CogQuest, ToontownGlobals.DonaldsDock, 5, 'mm'), Same, Same, NA, 2212,
           TTLocalizer.QuestDialogDict[2211]),
    2212: (DD_TIER + 2, Cont, (DeliverItemQuest, 2006), Same, 1302, NA, 2213,
           TTLocalizer.QuestDialogDict[2212]),
    2213: (DD_TIER + 2, Cont, (VisitQuest,), Same, 1202, NA, 2214,
           TTLocalizer.QuestDialogDict[2213]),
    2214: (DD_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.DonaldsDock, 3, 2007, Hard, Any), Same, Same, NA, 2215,
           TTLocalizer.QuestDialogDict[2214]),
    2215: (DD_TIER + 2, Cont, (DeliverItemQuest, 2008), Same, 1302, 301, NA,
           TTLocalizer.QuestDialogDict[2215]),

    # Collect salty sprockets from cogs in the neighborhood, and then deliver them to Admiral Hook in to carry 40 gags
    2500: (DD_TIER + 2, Start, (DeliverItemQuest, 2013), ToonHQ, 1105, NA, 2501, TTLocalizer.QuestDialogDict[2500]),
    2501: (
        DD_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.DonaldsDock, 5, 2014, Medium, 'bc'), Same, Same, 203, NA,
        TTLocalizer.QuestDialogDict[2501]),

    # Optional quests to do while working on the bottleneck quest
    2801: (DD_TIER + 2, Start, (CogQuest, Anywhere, 3, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2802: (DD_TIER + 2, Start, (CogQuest, Anywhere, 4, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2803: (DD_TIER + 2, Start, (CogQuest, Anywhere, 5, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2804: (DD_TIER + 2, Start, (CogQuest, Anywhere, 6, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2805: (DD_TIER + 2, Start, (CogQuest, Anywhere, 7, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2806: (DD_TIER + 2, Start, (CogQuest, Anywhere, 8, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2807: (DD_TIER + 2, Start, (CogQuest, Anywhere, 9, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2808: (DD_TIER + 2, Start, (CogQuest, Anywhere, 10, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2809: (DD_TIER + 2, Start, (CogQuest, Anywhere, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    2810: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 2, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2811: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 3, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    2812: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 2, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2813: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 4, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    2814: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 4, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2815: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 5, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    2816: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 4, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2817: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 5, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2818: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 6, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    2819: (DD_TIER + 2, Start, (CogLevelQuest, Anywhere, 7, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    # Ahab is building a giant prefab crab to confuse the cogs. He will need several cog
    # parts for it. Go see Claggart to get a clovis. Go see Hook to get a clock spring. Get a
    # counter weight from Rocky Shores (or Svetlana, or Cal). Then remove a cog building
    # that's blocking the solar panel on the crab.
    901: (DD_TIER + 2, Start, (VisitQuest,), Any, 1203, NA, 2902,
          TTLocalizer.QuestDialogDict[901]),
    2902: (DD_TIER + 2, Start, (VisitQuest,), 1203, 1303, NA, 2903,
           TTLocalizer.QuestDialogDict[2902]),
    2903: (DD_TIER + 2, Cont, (DeliverItemQuest, 2009), Same, 1106, NA, 2904,
           TTLocalizer.QuestDialogDict[2903]),
    2904: (DD_TIER + 2, Cont, (DeliverItemQuest, 2010), Same, 1203, NA, 2905,
           TTLocalizer.QuestDialogDict[2904]),
    2905: (DD_TIER + 2, Cont, (VisitQuest, 2009), Same, 1105, NA, 2906,
           TTLocalizer.QuestDialogDict[2905]),
    2906: (DD_TIER + 2, Cont, (DeliverGagQuest, 3, ToontownBattleGlobals.SQUIRT_TRACK, 2), Same, Same, NA, 2907,
           TTLocalizer.QuestDialogDict[2906]),
    2907: (DD_TIER + 2, Cont, (DeliverItemQuest, 2011), Same, 1203, NA, (2910, 2915, 2920),
           TTLocalizer.QuestDialogDict[2907]),
    2910: (DD_TIER + 2, Cont, (VisitQuest,), Same, 1107, NA, 2911, TTLocalizer.QuestDialog_2910),
    2911: (DD_TIER + 2, Cont, (CogTrackQuest, ToontownGlobals.DonaldsDock, 4, 'm'), Same, Same, NA, 2925,
           TTLocalizer.QuestDialogDict[2911]),
    2915: (DD_TIER + 2, Cont, (VisitQuest,), Same, 1204, NA, 2916, TTLocalizer.QuestDialog_2910),
    2916: (DD_TIER + 2, Cont, (CogTrackQuest, ToontownGlobals.DonaldsDock, 2, 's'), Same, Same, NA, 2925,
           TTLocalizer.QuestDialogDict[2916]),
    2920: (DD_TIER + 2, Cont, (VisitQuest,), Same, 1204, NA, 2921, TTLocalizer.QuestDialog_2910),
    2921: (DD_TIER + 2, Cont, (CogTrackQuest, ToontownGlobals.DonaldsDock, 6, 'c'), Same, Same, NA, 2925,
           TTLocalizer.QuestDialogDict[2921]),
    2925: (DD_TIER + 2, Cont, (DeliverItemQuest, 2012), Same, 1203, NA, 2926,
           TTLocalizer.QuestDialogDict[2925]),
    2926: (DD_TIER + 2, Cont, (BuildingQuest, ToontownGlobals.DonaldsDock, 1, Any, 2), Same, Same, 804, NA,
           TTLocalizer.QuestDialogDict[2926]),

    # Daisy Garden
    3101: (DG_TIER, Start, (CogQuest, ToontownGlobals.DaisyGardens, 8, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    3102: (DG_TIER, Start, (CogQuest, ToontownGlobals.DaisyGardens, 10, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    3103: (DG_TIER, Start, (CogQuest, ToontownGlobals.DaisyGardens, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    3104: (DG_TIER, Start, (CogQuest, Anywhere, 14, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    3105: (DG_TIER, Start, (CogQuest, Anywhere, 16, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    3106: (DG_TIER, Start, (CogQuest, Anywhere, 18, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    # DG is heavy on sellbots and lawbots; few bossbots or cashbots here.
    3107: (DG_TIER, Start, (CogQuest, Anywhere, 10, 'f'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3108: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'p'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3109: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'ym'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3110: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'mm'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3111: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'ds'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3112: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'hh'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),

    3113: (DG_TIER, Start, (CogQuest, Anywhere, 10, 'cc'), Any, ToonHQ, Any, NA, DefaultDialog),
    3114: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),
    3115: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'nd'), Any, ToonHQ, Any, NA, DefaultDialog),
    3116: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'gh'), Any, ToonHQ, Any, NA, DefaultDialog),
    3117: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),
    3118: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),

    3119: (DG_TIER, Start, (CogQuest, Anywhere, 10, 'sc'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3120: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'pp'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3121: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'tw'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3122: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'bc'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3123: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'nc'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3124: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'mb'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),

    3125: (DG_TIER, Start, (CogQuest, Anywhere, 10, 'bf'), Any, ToonHQ, Any, NA, DefaultDialog),
    3126: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    3127: (DG_TIER, Start, (CogQuest, Anywhere, 8, 'dt'), Any, ToonHQ, Any, NA, DefaultDialog),
    3128: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'ac'), Any, ToonHQ, Any, NA, DefaultDialog),
    3129: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),
    3130: (DG_TIER, Start, (CogQuest, Anywhere, 6, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),

    3131: (DG_TIER, Start, (CogLevelQuest, Anywhere, 10, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    3132: (DG_TIER, Start, (CogLevelQuest, Anywhere, 15, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    3133: (DG_TIER, Start, (CogLevelQuest, Anywhere, 8, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    3134: (DG_TIER, Start, (CogLevelQuest, Anywhere, 12, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    3135: (DG_TIER, Start, (CogLevelQuest, Anywhere, 4, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    3136: (DG_TIER, Start, (CogLevelQuest, Anywhere, 6, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    3137: (DG_TIER, Start, (CogLevelQuest, Anywhere, 8, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    3138: (DG_TIER, Start, (CogLevelQuest, Anywhere, 12, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    3139: (
        DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 6, 'm'), Any, ToonHQ, OBSOLETE, NA,
        DefaultDialog),
    3140: (DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 6, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    3141: (
        DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 6, 'c'), Any, ToonHQ, OBSOLETE, NA,
        DefaultDialog),
    3142: (DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 6, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    3143: (
        DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 10, 'm'), Any, ToonHQ, OBSOLETE, NA,
        DefaultDialog),
    3144: (DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 10, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    3145: (
        DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 10, 'c'), Any, ToonHQ, OBSOLETE, NA,
        DefaultDialog),
    3146: (DG_TIER, Start, (CogTrackQuest, ToontownGlobals.DaisyGardens, 10, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    3147: (DG_TIER, Start, (CogTrackQuest, Anywhere, 14, 'm'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3148: (DG_TIER, Start, (CogTrackQuest, Anywhere, 14, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    3149: (DG_TIER, Start, (CogTrackQuest, Anywhere, 14, 'c'), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3150: (DG_TIER, Start, (CogTrackQuest, Anywhere, 14, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    3151: (DG_TIER, Start, (BuildingQuest, Anywhere, 1, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    3152: (DG_TIER, Start, (BuildingQuest, Anywhere, 2, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    3153: (DG_TIER, Start, (BuildingQuest, Anywhere, 3, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    3154: (DG_TIER, Start, (BuildingQuest, Anywhere, 4, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    3155: (DG_TIER, Start, (BuildingQuest, Anywhere, 2, 'm', 2), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3156: (DG_TIER, Start, (BuildingQuest, Anywhere, 2, 's', 2), Any, ToonHQ, Any, NA, DefaultDialog),
    3157: (DG_TIER, Start, (BuildingQuest, Anywhere, 2, 'c', 2), Any, ToonHQ, OBSOLETE, NA, DefaultDialog),
    3158: (DG_TIER, Start, (BuildingQuest, Anywhere, 2, 'l', 2), Any, ToonHQ, Any, NA, DefaultDialog),

    # Artie of Artie Choke's Neckties wants you to take a silk necktie
    # to Vine and Dandy menswear.  The shopkeeper at Vine and Dandy
    # complains that the matching suit was stolen last week, and sends
    # you out to recover that.  Reward: +1 Laff.
    3200: (DG_TIER, Start, (VisitQuest,), Any, 5101, NA, 3201,
           TTLocalizer.QuestDialogDict[3200]),
    3201: (DG_TIER, Start, (DeliverItemQuest, 5001), 5101, 5206, NA, 3203,
           TTLocalizer.QuestDialogDict[3201]),
    3203: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 1, 5002, VeryHard, Any), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3203]),

    # The barber at Crop Top Barbers has lost a pair of scissors.  He
    # thinks a Bloodsucker stole it.  Reward: +1 Laff.
    3204: (DG_TIER, Start, (VisitQuest,), Any, 5106, NA, 3205,
           TTLocalizer.QuestDialogDict[3204]),
    3205: (DG_TIER, Start, (RecoverItemQuest, Anywhere, 1, 5003, Medium, 'b'), 5106, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3205]),

    # The post officer in Compost Office complains that a bunch of
    # Double Talkers broke in and stole a stack of postcards from his
    # mailbox.  Recover all ten postcards.  Reward: +2 Laff.
    3206: (DG_TIER, Start, (VisitQuest,), Any, 5107, NA, 3207,
           TTLocalizer.QuestDialogDict[3206]),
    3207: (
        DG_TIER, Start, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 10, 5004, VeryEasy, 'dt'), 5107, Same, 101, NA,
        TTLocalizer.QuestDialogDict[3207]),

    # OBSOLETE: This quest has been made obsolete to make room for the Sellbot Cog HQ Quest
    # We've been getting complaints from the residents about all the
    # cold callers.  Thin these out a bit.  Then go after the
    # telemarketers too.  Reward: 40 carry
    3208: (DG_TIER, OBSOLETE, (CogQuest, ToontownGlobals.DaisyGardens, 10, 'cc'), Any, ToonHQ, NA, 3209,
           TTLocalizer.QuestDialogDict[3208]),
    3209: (DG_TIER, OBSOLETE, (CogQuest, ToontownGlobals.DaisyGardens, 10, 'tm'), Same, Same, 203, NA,
           TTLocalizer.QuestDialogDict[3209]),

    # OBSOLETE: This quest has been made obsolete to make room for the
    # Sellbot Cog HQ Quest. We've been getting complaints from the residents
    # about all the blood suckers.  Thin these out a bunch.  Reward: 40 carry
    3247: (DG_TIER, OBSOLETE, (CogQuest, ToontownGlobals.DaisyGardens, 20, 'b'), Any, ToonHQ, 203, NA,
           TTLocalizer.QuestDialogDict[3247]),

    # Oh no, Gopher is out of gags!  Bring them ten of yours.
    # Then clear the street of cogs.  Reward: +1 Laff.
    3210: (DG_TIER, Start, (DeliverGagQuest, 10, 2), Any, 5120, NA, 3211,
           TTLocalizer.QuestDialogDict[3210]),
    3211: (DG_TIER, Cont, (CogQuest, 5100, 8, Any), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3211]),

    # OBSOLETE: This quest has been made obsolete to make room for the
    # Sellbot Cog HQ Quest Trellis the Truth has lost a lot of office
    # supplies.  Reward: small bag (35 carry).
    3212: (DG_TIER, OBSOLETE, (VisitQuest,), Any, 5208, NA, 3213,
           TTLocalizer.QuestDialogDict[3212]),
    3213: (
        DG_TIER, OBSOLETE, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 1, 5005, VeryHard, Any), 5208, Same, NA,
        3214,
        TTLocalizer.QuestDialogDict[3213]),
    3214: (
        DG_TIER, OBSOLETE, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 1, 5006, VeryHard, Any), Same, Same, NA,
        3215,
        TTLocalizer.QuestDialogDict[3214]),
    3215: (
        DG_TIER, OBSOLETE, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 1, 5007, VeryHard, Any), Same, Same, NA,
        3216,
        TTLocalizer.QuestDialogDict[3215]),
    3216: (
        DG_TIER, OBSOLETE, (RecoverItemQuest, ToontownGlobals.DaisyGardens, 1, 5008, VeryHard, Any), Same, Same, 203,
        NA,
        TTLocalizer.QuestDialogDict[3216]),

    # We're studying sprockets from Sellbots.  Get us a sprocket from a Glad Hander.
    # Then, get one from a Mover & Shaker.  Reward: +1 Laff.
    3217: (DG_TIER, Start, (RecoverItemQuest, Anywhere, 1, 5010, Hard, 'gh'), ToonHQ, ToonHQ, NA, 3218,
           TTLocalizer.QuestDialogDict[3217]),
    3218: (DG_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 5010, Hard, 'ms'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3218]),

    # We're studying sprockets from Lawbots.  Get us a sprocket from a Back Stabber.
    # Then, get one from a Spin Doctor.  Reward: +1 Laff.
    3244: (DG_TIER, Start, (RecoverItemQuest, Anywhere, 1, 5010, Hard, 'bs'), ToonHQ, ToonHQ, NA, 3245,
           TTLocalizer.QuestDialogDict[3244]),
    3245: (DG_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 5010, Medium, 'sd'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3245]),

    # The Squirting Flower wants you to set a good example for your
    # fellow toons with your squirt attacks.  Go clobber a bunch of
    # cogs.  Reward: +1 Laff.
    3220: (DG_TIER, Start, (VisitQuest,), Any, 5207, NA, 3221,
           TTLocalizer.QuestDialogDict[3220]),
    3221: (DG_TIER, Start, (CogQuest, ToontownGlobals.DaisyGardens, 12, Any), 5207, Same, 100, NA,
           TTLocalizer.QuestDialogDict[3221]),

    # Demonstrate your skills.  First, take back a two-story building;
    # then a three-story building; then one more four-story building.
    # Reward: carry three quests.
    3222: (DG_TIER, Start, (BuildingQuest, Anywhere, 1, Any, 2), ToonHQ, ToonHQ, NA, 3223,
           TTLocalizer.QuestDialogDict[3222]),
    3223: (DG_TIER, Cont, (BuildingQuest, Anywhere, 1, Any, 3), Same, Same, NA, 3224,
           TTLocalizer.QuestDialogDict[3223]),
    3224: (DG_TIER, Cont, (BuildingQuest, Anywhere, 1, Any, 4), Same, Same, 501, NA,
           TTLocalizer.QuestDialogDict[3224]),

    # The cogs have frightened away The Dew Drop Inn's delivery
    # person.  They need someone to deliver a salad to one of several
    # possible neighborhood persons who ordered one.  Then defeat some
    # cogs.  Reward: +1 Laff.
    3225: (DG_TIER, Start, (VisitQuest,), Any, 5108, NA, (3226, 3227, 3228, 3229, 3230, 3231, 3232, 3233, 3234),
           TTLocalizer.QuestDialogDict[3225]),
    3226: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5201, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3227: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5203, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3228: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5204, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3229: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5205, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3230: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5102, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3231: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5103, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3232: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5104, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3233: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5105, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3234: (DG_TIER, Start, (DeliverItemQuest, 5011), 5108, 5207, NA, 3235,
           TTLocalizer.QuestDialog_3225),
    3235: (DG_TIER, Cont, (CogQuest, ToontownGlobals.DaisyGardens, 8, Any), Same, 5108, 100, NA,
           TTLocalizer.QuestDialogDict[3235]),

    # OBSOLETE: This quest has been made obsolete to make room for the Sellbot Cog HQ Quest
    # Too many Lawbots!  Reclaim 3 lawbot buildings.  Oops, now too
    # many Sellbots!  Reclaim 3 sellbot buildings.  Reward: 80 max jellybeans.
    3236: (DG_TIER, OBSOLETE, (BuildingQuest, Anywhere, 3, 'l', 2), Any, ToonHQ, NA, 3237,
           TTLocalizer.QuestDialogDict[3236]),
    3237: (DG_TIER, OBSOLETE, (BuildingQuest, Anywhere, 3, 's', 2), Same, Same, 805, NA,
           TTLocalizer.QuestDialogDict[3237]),

    # The Mingler has stolen the Key to Daisy Gardens.  Reclaim it
    # from him.  Oops, not that key, some other one!  Reward: teleport
    # access to Daisy Gardens.
    3238: (DG_TIER, Start, (RecoverItemQuest, Anywhere, 1, 2, VeryEasy, 'm'), Any, ToonHQ, NA, 3239,
           TTLocalizer.QuestDialogDict[3238]),
    3239: (DG_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 5012, Hard, 'm'), Same, Same, 302, NA,
           TTLocalizer.QuestDialogDict[3239]),

    # A Legal Eagle has stolen the Key to Daisy Gardens.  Reclaim it
    # from him.  Oops, not that key, some other one!  Reward: teleport
    # access to Daisy Gardens.
    3242: (DG_TIER, Start, (RecoverItemQuest, Anywhere, 1, 2, VeryEasy, 'le'), Any, ToonHQ, NA, 3243,
           TTLocalizer.QuestDialogDict[3242]),
    3243: (DG_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 5012, Hard, 'le'), Same, Same, 302, NA,
           TTLocalizer.QuestDialogDict[3243]),

    # OBSOLETE: These two quests have been removed to make way for the Cog HQ quests
    # A Legal Eagle stole a bag of bird seed from Bud's Bird Seed.
    # Reward: +3 Laff.
    3240: (DG_TIER, OBSOLETE, (RecoverItemQuest, Anywhere, 1, 5009, Hard, 'le'), Any, 5103, 102, NA,
           TTLocalizer.QuestDialogDict[3240]),

    # OBSOLETE: Recover 5 3+-story buildings.  Reward: +3 Laff.
    3241: (DG_TIER, OBSOLETE, (BuildingQuest, Anywhere, 5, Any, 3), Any, ToonHQ, 102, NA,
           TTLocalizer.QuestDialogDict[3241]),

    # Visit Detective Lima, defeat 5 Sellbots in Sellbot HQ, visit Judge
    # McIntosh, recover Sellbot HQ blueprints, deliver blueprints to
    # Detective Lima. Reward: 45 carry
    3250: (DG_TIER, Start, (VisitQuest,), Any, 5317, NA, 3251,
           TTLocalizer.QuestDialogDict[3250]),
    3251: (DG_TIER, Start, (CogTrackQuest, ToontownGlobals.SellbotHQ, 5, 's'), 5317, Same, NA, 3252,
           TTLocalizer.QuestDialogDict[3251]),
    3252: (DG_TIER, Cont, (VisitQuest,), Same, 5311, NA, 3253,
           TTLocalizer.QuestDialogDict[3252]),
    3253: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.SellbotHQ, 1, 5013, Medium, 's', 'track'),
           Same, Same, NA, 3254, TTLocalizer.QuestDialogDict[3253]),
    3254: (DG_TIER, Cont, (DeliverItemQuest, 5013), Same, 5317, 204, NA,
           TTLocalizer.QuestDialogDict[3254]),

    # Quest: Sellbot HQ Memos
    # Reward: +2 laff points (101)
    # Splits into 3 separate NPCs to avoid crowding
    3255: (DG_TIER, Start, (VisitQuest,), Any, 5314, NA, 3258,
           TTLocalizer.QuestDialogDict[3255]),
    3256: (DG_TIER, Start, (VisitQuest,), Any, 5315, NA, 3258,
           TTLocalizer.QuestDialogDict[3256]),
    3257: (DG_TIER, Start, (VisitQuest,), Any, 5316, NA, 3258,
           TTLocalizer.QuestDialogDict[3257]),
    3258: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.SellbotHQ, 1, 5014, VeryEasy, 's', 'track'),
           Same, Same, NA, 3259, TTLocalizer.QuestDialogDict[3258]),
    3259: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.SellbotHQ, 1, 5015, Easy, 's', 'track'),
           Same, Same, NA, 3260, TTLocalizer.QuestDialogDict[3259]),
    3260: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.SellbotHQ, 1, 5016, Easy, 's', 'track'),
           Same, Same, NA, 3261, TTLocalizer.QuestDialogDict[3260]),
    3261: (DG_TIER, Cont, (RecoverItemQuest, ToontownGlobals.SellbotHQ, 1, 5017, Medium, 's', 'track'),
           Same, Same, 101, NA, TTLocalizer.QuestDialogDict[3261]),

    # Visit Coach Zucchini, Then defeat the Sellbot HQ Factory.
    # Reward: +3 Laff
    3262: (DG_TIER, Start, (VisitQuest,), Any, 5313, NA, 3263,
           TTLocalizer.QuestDialogDict[3262]),
    3263: (DG_TIER, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 1), 5313, 5313, 102, NA,
           TTLocalizer.QuestDialogDict[3263]),

    # Visit Detective Lima, Then defeat 10 level 4+ cogs in the Sellbot HQ Factory.
    # Reward: Training Frame #5
    3264: (DG_TIER, Start, (VisitQuest,), Any, 5313, NA, 3265,
           TTLocalizer.QuestDialogDict[3264]),
    3265: (DG_TIER, Start, (CogLevelQuest, ToontownGlobals.SellbotFactoryInt, 10, 4), 5313, 5313, 805, NA,
           TTLocalizer.QuestDialogDict[3265]),

    # Visit Coach Zucchini, Then defeat 8 skelecogs in the Sellbot HQ Factory.
    # Reward: Training Frame #6
    3266: (DG_TIER + 1, Start, (VisitQuest,), Any, 5313, NA, 3265,
           TTLocalizer.QuestDialogDict[3266]),
    3267: (DG_TIER + 1, Start, (SkelecogQuest, ToontownGlobals.SellbotFactoryInt, 8), 5313, 5313, 806, NA,
           TTLocalizer.QuestDialogDict[3267]),

    # Defeat cogs in Sellbot HQ, then deliver reports to Prof. Pete.
    # Reward: Carry 50 Gags
    3268: (DG_TIER + 1, Start, (CogQuest, ToontownGlobals.SellbotHQ, 25, Any), Any, ToonHQ, NA, 3269,
           TTLocalizer.QuestDialogDict[3268]),
    3269: (DG_TIER + 1, Cont, (DeliverItemQuest, 1302), Same, 2003, 205, NA, TTLocalizer.QuestDialogDict[3269]),

    # Next DG_TIER id: 3270-3999

    # Minnies melodyland
    4001: (MM_TIER, Start, (VisitQuest,), Any, ToonHQ, 401, NA, TTLocalizer.QuestDialogDict[4001]),

    # Optional quests to do while working on the bottleneck quest
    4010: (MM_TIER, Start, (CogQuest, Anywhere, 16, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4011: (MM_TIER, Start, (CogQuest, Anywhere, 18, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4012: (MM_TIER, Start, (CogQuest, Anywhere, 20, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4013: (MM_TIER, Start, (CogQuest, Anywhere, 22, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4014: (MM_TIER, Start, (CogQuest, Anywhere, 24, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4015: (MM_TIER, Start, (CogQuest, Anywhere, 26, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4016: (MM_TIER, Start, (CogQuest, Anywhere, 28, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4017: (MM_TIER, Start, (CogQuest, Anywhere, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4018: (MM_TIER, Start, (CogQuest, Anywhere, 32, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4019: (MM_TIER, Start, (CogQuest, Anywhere, 34, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4020: (MM_TIER, Start, (CogLevelQuest, Anywhere, 20, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    4021: (MM_TIER, Start, (CogLevelQuest, Anywhere, 25, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    4022: (MM_TIER, Start, (CogLevelQuest, Anywhere, 16, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4023: (MM_TIER, Start, (CogLevelQuest, Anywhere, 20, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4024: (MM_TIER, Start, (CogLevelQuest, Anywhere, 10, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4025: (MM_TIER, Start, (CogLevelQuest, Anywhere, 20, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4026: (MM_TIER, Start, (CogLevelQuest, Anywhere, 16, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4027: (MM_TIER, Start, (CogLevelQuest, Anywhere, 18, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4028: (MM_TIER, Start, (CogLevelQuest, Anywhere, 20, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4029: (MM_TIER, Start, (CogLevelQuest, Anywhere, 24, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    # Cashbot HQ quests
    4040: (MM_TIER, Start, (CogQuest, ToontownGlobals.CashbotHQ, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4041: (MM_TIER, Start, (CogQuest, ToontownGlobals.CashbotMintIntA, 10, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4042: (MM_TIER, Start, (CogLevelQuest, ToontownGlobals.CashbotHQ, 5, 9), Any, ToonHQ, Any, NA, DefaultDialog),
    4043: (MM_TIER, Start, (SkelecogQuest, ToontownGlobals.CashbotHQ, 8), Any, ToonHQ, Any, NA, DefaultDialog),

    # MM is a little heavy on money (cashbot) cogs, but has a fairly
    # good cog distribution otherwise.  The sellbots in MM are
    # mostly level 2..4, while other type cogs are level 3..6.

    4101: (MM_TIER + 1, Start, (CogQuest, ToontownGlobals.MinniesMelodyland, 12, Any), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4102: (MM_TIER + 1, Start, (CogQuest, ToontownGlobals.MinniesMelodyland, 16, Any), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4103: (MM_TIER + 1, Start, (CogQuest, Anywhere, 25, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4104: (MM_TIER + 1, Start, (CogQuest, Anywhere, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    4105: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'p'), Any, ToonHQ, Any, NA, DefaultDialog),
    4106: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'ym'), Any, ToonHQ, Any, NA, DefaultDialog),
    4107: (MM_TIER + 1, Start, (CogQuest, Anywhere, 8, 'mm'), Any, ToonHQ, Any, NA, DefaultDialog),
    4108: (MM_TIER + 1, Start, (CogQuest, Anywhere, 6, 'ds'), Any, ToonHQ, Any, NA, DefaultDialog),

    4109: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'tm'), Any, ToonHQ, Any, NA, DefaultDialog),
    4110: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'nd'), Any, ToonHQ, Any, NA, DefaultDialog),
    4111: (MM_TIER + 1, Start, (CogQuest, Anywhere, 8, 'gh'), Any, ToonHQ, Any, NA, DefaultDialog),
    4112: (MM_TIER + 1, Start, (CogQuest, Anywhere, 6, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),

    4113: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'pp'), Any, ToonHQ, Any, NA, DefaultDialog),
    4114: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'tw'), Any, ToonHQ, Any, NA, DefaultDialog),
    4115: (MM_TIER + 1, Start, (CogQuest, Anywhere, 8, 'bc'), Any, ToonHQ, Any, NA, DefaultDialog),
    4116: (MM_TIER + 1, Start, (CogQuest, Anywhere, 6, 'nc'), Any, ToonHQ, Any, NA, DefaultDialog),

    4117: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'b'), Any, ToonHQ, Any, NA, DefaultDialog),
    4118: (MM_TIER + 1, Start, (CogQuest, Anywhere, 10, 'dt'), Any, ToonHQ, Any, NA, DefaultDialog),
    4119: (MM_TIER + 1, Start, (CogQuest, Anywhere, 8, 'ac'), Any, ToonHQ, Any, NA, DefaultDialog),
    4120: (MM_TIER + 1, Start, (CogQuest, Anywhere, 6, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),

    4121: (MM_TIER + 1, Start, (CogLevelQuest, Anywhere, 20, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4122: (MM_TIER + 1, Start, (CogLevelQuest, Anywhere, 15, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4123: (MM_TIER + 1, Start, (CogLevelQuest, Anywhere, 10, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    4124: (MM_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.MinniesMelodyland, 10, 'm'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4125: (MM_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.MinniesMelodyland, 10, 's'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4126: (MM_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.MinniesMelodyland, 10, 'c'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4127: (MM_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.MinniesMelodyland, 10, 'l'), Any, ToonHQ, Any, NA,
           DefaultDialog),

    4128: (MM_TIER + 1, Start, (CogTrackQuest, Anywhere, 16, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    4129: (MM_TIER + 1, Start, (CogTrackQuest, Anywhere, 16, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    4130: (MM_TIER + 1, Start, (CogTrackQuest, Anywhere, 16, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    4131: (MM_TIER + 1, Start, (CogTrackQuest, Anywhere, 16, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    4132: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 3, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    4133: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    4134: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 1, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4135: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'm', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4136: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 's', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4137: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'c', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4138: (MM_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'l', 4), Any, ToonHQ, Any, NA, DefaultDialog),

    # Cashbot HQ quests
    4161: (MM_TIER + 1, Start, (CogQuest, ToontownGlobals.CashbotHQ, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4162: (MM_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.CashbotHQ, 8, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    4163: (MM_TIER + 1, Start, (MintQuest, ToontownGlobals.CashbotMintIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4164: (MM_TIER + 1, Start, (MintQuest, ToontownGlobals.CashbotMintIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4165: (MM_TIER + 1, Start, (MintQuest, ToontownGlobals.CashbotMintIntC, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4166: (MM_TIER + 1, Start, (SkelecogQuest, ToontownGlobals.CashbotHQ, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    4167: (MM_TIER + 1, Start, (SupervisorQuest, ToontownGlobals.CashbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4168: (MM_TIER + 1, Start, (SupervisorQuest, ToontownGlobals.CashbotMintIntB, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),

    # Reward: 55 Carry
    # Tom's collecting info on how many musical instruments have gone missing since the
    # cog invasion. Run around to the following vendors and get inventory sheets:
    #   Tina's Concertina Concerts, Yuki's Ukelele's, Fifi's Fiddles
    4200: (MM_TIER + 1, Start, (VisitQuest,), Any, 4101, NA, 4201,
           TTLocalizer.QuestDialogDict[4200]),
    4201: (MM_TIER + 1, Start, (VisitQuest,), 4101, 4201, NA, 4202,
           TTLocalizer.QuestDialogDict[4201]),
    4202: (MM_TIER + 1, Cont, (DeliverItemQuest, 4001), Same, 4101, NA, 4203,
           TTLocalizer.QuestDialogDict[4202]),
    4203: (MM_TIER + 1, Cont, (VisitQuest,), Same, 4301, NA, 4204,
           TTLocalizer.QuestDialogDict[4203]),
    4204: (MM_TIER + 1, Cont, (CogQuest, ToontownGlobals.MinniesMelodyland, 10, Any), Same, Same, NA, 4205,
           TTLocalizer.QuestDialogDict[4204]),
    4205: (MM_TIER + 1, Cont, (DeliverItemQuest, 4002), Same, 4101, NA, 4206,
           TTLocalizer.QuestDialogDict[4205]),
    4206: (MM_TIER + 1, Cont, (VisitQuest,), Same, 4102, NA, 4207,
           TTLocalizer.QuestDialogDict[4206]),
    4207: (MM_TIER + 1, Cont, (VisitQuest,), Same, 4108, NA, 4208,
           TTLocalizer.QuestDialogDict[4207]),
    4208: (MM_TIER + 1, Cont, (DeliverGagQuest, 1, 4), Same, Same, NA, 4209,
           TTLocalizer.QuestDialogDict[4208]),
    4209: (MM_TIER + 1, Cont, (DeliverItemQuest, 4003), Same, 4102, NA, 4210,
           TTLocalizer.QuestDialogDict[4209]),
    4210: (MM_TIER + 1, Cont, (DeliverItemQuest, 4004), Same, 4101, 206, NA,
           TTLocalizer.QuestDialogDict[4210]),

    # 303: MM teleport access
    # Dr. Fret is having trouble getting customers. First he thinks its the Number Crunchers
    # that are scaring everyone away. Then he think its cashbots in general. Finally he asks
    # you take over a cog building before he remembers that he never really had any customers
    # to speak of...
    4211: (MM_TIER + 1, Start, (VisitQuest,), ToonHQ, 4103, NA, 4212,
           TTLocalizer.QuestDialogDict[4211]),
    4212: (MM_TIER + 1, Start, (CogQuest, ToontownGlobals.MinniesMelodyland, 10, 'nc'), 4103, Same, NA, 4213,
           TTLocalizer.QuestDialogDict[4212]),
    4213: (MM_TIER + 1, Cont, (CogTrackQuest, ToontownGlobals.MinniesMelodyland, 20, 'm'), Same, Same, NA, 4214,
           TTLocalizer.QuestDialogDict[4213]),
    4214: (MM_TIER + 1, Cont, (BuildingQuest, Anywhere, 1, 'm', Any), Same, Same, 303, NA,
           TTLocalizer.QuestDialogDict[4214]),

    # 807: Training Frame #7
    # Gladhanders' have made off with Anna's customers' travel tickets. Retrieve them and
    # then deliver them to the following people:
    #   Lumber Jack, Tabitha, Barry 
    4215: (MM_TIER + 1, Start, (VisitQuest,), Any, 4302, NA, 4216,
           TTLocalizer.QuestDialogDict[4215]),
    4216: (MM_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 4005, Medium, 'gh'), 4302, Same, NA, 4217,
           TTLocalizer.QuestDialogDict[4216]),
    4217: (MM_TIER + 1, Cont, (DeliverItemQuest, 4005), Same, 4203, NA, 4218,
           TTLocalizer.QuestDialogDict[4217]),
    4218: (MM_TIER + 1, Cont, (VisitQuest,), Any, 4302, NA, 4219,
           TTLocalizer.QuestDialogDict[4218]),
    4219: (MM_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 4006, Medium, 'gh'), Same, Same, NA, 4220,
           TTLocalizer.QuestDialogDict[4219]),
    4220: (MM_TIER + 1, Cont, (DeliverItemQuest, 4006), Same, 4308, NA, 4221,
           TTLocalizer.QuestDialogDict[4220]),
    4221: (MM_TIER + 1, Cont, (VisitQuest,), Any, 4302, NA, 4222,
           TTLocalizer.QuestDialogDict[4221]),
    4222: (MM_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 4007, Hard, 'gh'), Same, Same, NA, 4223,
           TTLocalizer.QuestDialogDict[4222]),
    4223: (MM_TIER + 1, Cont, (DeliverItemQuest, 4007), Same, 4202, NA, 4224,
           TTLocalizer.QuestDialogDict[4223]),
    4224: (MM_TIER + 1, Cont, (VisitQuest,), Any, 4302, 807, NA,
           TTLocalizer.QuestDialogDict[4224]),

    # Defeat 3 Cog buildings, then deliver the production notice to Professor Pete.  Reward: 60 Max Carry
    4225: (MM_TIER + 2, Start, (BuildingQuest, Anywhere, 3, Any, 1), Any, ToonHQ, NA, 4226,
           TTLocalizer.QuestDialogDict[4225]),
    4226: (MM_TIER + 2, Cont, (DeliverItemQuest, 1303), Same, 2003, 207, NA,
           TTLocalizer.QuestDialogDict[4226]),

    # 902: Training Frame #8
    # Visit Leo at Leo's Fenders. He's going to give a concert tonight and needs his castanets
    # polished. Bring them to Carlos who says he can do it, but needs some squid ink to make
    # them nice and black. After you return with the squid ink he will polish them but it will
    # take some time. Go reclaim a one story building in the mean time. Once you return the
    # polished castanets to Leo he asks you to go pick up the lyrics to "A Beatnik Christmas"
    # from Hedy at Lousy Lyrics. Hedy doesn't have a copy, but offers to transcribe it from
    # memory if you will reclaim a two story building on her street. Turns out it is taking
    # longer than she thought to remember the lyrics. Go reclaim a three story building. After
    # this she gives you the lyrics to take to Leo. Leo is overjoyed and give you a new frame.
    # 902 : ( MM_TIER+2, Start, (CogQuest, ToontownGlobals.MinniesMelodyland, 10, Any), Any, ToonHQ, 808, NA, DefaultDialog),
    902: (MM_TIER + 2, Start, (VisitQuest,), Any, 4303, NA, 4903,
          TTLocalizer.QuestDialogDict[902]),
    4903: (MM_TIER + 2, Start, (DeliverItemQuest, 4008), 4303, 4109, NA, 4904,
           TTLocalizer.QuestDialogDict[4903]),
    4904: (MM_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 4009, VeryHard, AnyFish), Same, Same, NA, 4905,
           TTLocalizer.QuestDialogDict[4904]),
    4905: (MM_TIER + 2, Cont, (BuildingQuest, Anywhere, 1, Any, 1), Same, Same, NA, 4906,
           TTLocalizer.QuestDialogDict[4905]),
    4906: (MM_TIER + 2, Cont, (DeliverItemQuest, 4010), Same, 4303, NA, 4907,
           TTLocalizer.QuestDialogDict[4906]),
    4907: (MM_TIER + 2, Cont, (VisitQuest,), Same, 4208, NA, 4908,
           TTLocalizer.QuestDialogDict[4907]),
    4908: (MM_TIER + 2, Cont, (BuildingQuest, Anywhere, 1, Any, 2), Same, Same, NA, 4909,
           TTLocalizer.QuestDialogDict[4908]),
    4909: (MM_TIER + 2, Cont, (BuildingQuest, Anywhere, 1, Any, 3), Same, Same, NA, 4910,
           TTLocalizer.QuestDialogDict[4909]),
    4910: (MM_TIER + 2, Cont, (DeliverItemQuest, 4011), Same, 4303, 808, NA,
           TTLocalizer.QuestDialogDict[4910]),

    # Optional quests to do while working on the bottleneck quest
    4810: (MM_TIER + 2, Start, (CogQuest, Anywhere, 16, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4811: (MM_TIER + 2, Start, (CogQuest, Anywhere, 18, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4812: (MM_TIER + 2, Start, (CogQuest, Anywhere, 20, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4813: (MM_TIER + 2, Start, (CogQuest, Anywhere, 22, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4814: (MM_TIER + 2, Start, (CogQuest, Anywhere, 24, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4815: (MM_TIER + 2, Start, (CogQuest, Anywhere, 26, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4816: (MM_TIER + 2, Start, (CogQuest, Anywhere, 28, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4817: (MM_TIER + 2, Start, (CogQuest, Anywhere, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4818: (MM_TIER + 2, Start, (CogQuest, Anywhere, 32, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4819: (MM_TIER + 2, Start, (CogQuest, Anywhere, 34, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4820: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    4821: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 25, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    4822: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 16, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4823: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4824: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 10, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4825: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4826: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 16, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4827: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 18, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4828: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    4829: (MM_TIER + 2, Start, (CogLevelQuest, Anywhere, 24, 6), Any, ToonHQ, Any, NA, DefaultDialog),

    # Cashbot HQ quests
    4840: (MM_TIER + 2, Start, (CogQuest, ToontownGlobals.SellbotHQ, 12, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4841: (MM_TIER + 2, Start, (CogQuest, ToontownGlobals.SellbotHQ, 15, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    4842: (MM_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.SellbotHQ, 12, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    4843: (
        MM_TIER + 2, Start, (CogLevelQuest, ToontownGlobals.SellbotFactoryInt, 10, 5), Any, ToonHQ, Any, NA,
        DefaultDialog),
    4844: (MM_TIER + 2, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4845: (MM_TIER + 2, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    4846: (
        MM_TIER + 2, Start, (SkelecogQuest, ToontownGlobals.SellbotFactoryInt, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4847: (
        MM_TIER + 2, Start, (SkelecogLevelQuest, ToontownGlobals.SellbotHQ, 3, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    4848: (MM_TIER + 2, Start, (ForemanQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # The Brrrgh
    # We will pick one of these quests depending on what the avatar chose previously
    5247: (BR_TIER, Start, (VisitQuest,), Any, 3112, NA, 5248,
           TTLocalizer.QuestDialogDict[5247]),
    5248: (BR_TIER, Start, (CogLevelQuest, Anywhere, 10, 8), 3112, Same, NA, 5249,
           TTLocalizer.QuestDialogDict[5248]),
    5249: (BR_TIER, Cont, (RecoverItemQuest, Anywhere, 3, 3018, VeryHard, AnyFish), Same, Same, NA,
           (5250, 5258, 5259, 5260), TTLocalizer.QuestDialogDict[5249]),
    5250: (BR_TIER, Cont, (BuildingQuest, Anywhere, 1, "l", 4), Same, Same, NA, 5001,
           TTLocalizer.QuestDialogDict[5250]),
    5258: (BR_TIER, Cont, (BuildingQuest, Anywhere, 1, "c", 4), Same, Same, NA, 5001,
           TTLocalizer.QuestDialogDict[5258]),
    5259: (BR_TIER, Cont, (BuildingQuest, Anywhere, 1, "m", 4), Same, Same, NA, 5001,
           TTLocalizer.QuestDialogDict[5259]),
    5260: (BR_TIER, Cont, (BuildingQuest, Anywhere, 1, "s", 4), Same, Same, NA, 5001,
           TTLocalizer.QuestDialogDict[5260]),
    5001: (BR_TIER, Cont, (VisitQuest,), Same, Same, 403, NA, TTLocalizer.TheBrrrghTrackQuestDict),

    # Optional quests to do while working on the bottleneck quest
    5020: (BR_TIER, Start, (CogQuest, Anywhere, 36, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5021: (BR_TIER, Start, (CogQuest, Anywhere, 38, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5022: (BR_TIER, Start, (CogQuest, Anywhere, 40, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5023: (BR_TIER, Start, (CogQuest, Anywhere, 42, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5024: (BR_TIER, Start, (CogQuest, Anywhere, 44, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5025: (BR_TIER, Start, (CogQuest, Anywhere, 46, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5026: (BR_TIER, Start, (CogQuest, Anywhere, 48, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5027: (BR_TIER, Start, (CogQuest, Anywhere, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5028: (BR_TIER, Start, (CogQuest, Anywhere, 52, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5029: (BR_TIER, Start, (CogQuest, Anywhere, 54, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5030: (BR_TIER, Start, (CogLevelQuest, Anywhere, 25, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5031: (BR_TIER, Start, (CogLevelQuest, Anywhere, 30, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5032: (BR_TIER, Start, (CogLevelQuest, Anywhere, 35, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    5033: (BR_TIER, Start, (CogLevelQuest, Anywhere, 6, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5034: (BR_TIER, Start, (CogLevelQuest, Anywhere, 10, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5035: (BR_TIER, Start, (CogLevelQuest, Anywhere, 20, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5036: (BR_TIER, Start, (CogLevelQuest, Anywhere, 2, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5037: (BR_TIER, Start, (CogLevelQuest, Anywhere, 8, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5038: (BR_TIER, Start, (CogLevelQuest, Anywhere, 10, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5039: (BR_TIER, Start, (CogLevelQuest, Anywhere, 12, 8), Any, ToonHQ, Any, NA, DefaultDialog),

    # Lawbot HQ quests
    5071: (BR_TIER, Start, (CogQuest, ToontownGlobals.LawbotHQ, 24, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5072: (BR_TIER, Start, (CogLevelQuest, ToontownGlobals.LawbotHQ, 15, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5073: (BR_TIER, Start, (CogLevelQuest, ToontownGlobals.LawbotHQ, 10, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5074: (BR_TIER, Start, (CogLevelQuest, ToontownGlobals.LawbotStageIntA, 12, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5075: (BR_TIER, Start, (CogLevelQuest, ToontownGlobals.LawbotStageIntB, 10, 11), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5076: (BR_TIER, Start, (StageQuest, ToontownGlobals.LawbotStageIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5078: (BR_TIER, Start, (StageQuest, ToontownGlobals.LawbotStageIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5080: (BR_TIER, Start, (SkelecogQuest, ToontownGlobals.LawbotHQ, 16), Any, ToonHQ, Any, NA, DefaultDialog),
    5081: (BR_TIER, Start, (SkelecogLevelQuest, ToontownGlobals.LawbotHQ, 4, 11), Any, ToonHQ, Any, NA, DefaultDialog),
    5082: (BR_TIER, Start, (SkelecogLevelQuest, ToontownGlobals.LawbotHQ, 2, 12), Any, ToonHQ, Any, NA, DefaultDialog),
    5083: (BR_TIER, Start, (ClerkQuest, ToontownGlobals.LawbotStageIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5084: (BR_TIER, Start, (ClerkQuest, ToontownGlobals.LawbotStageIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # The Brrgh is heavy on corporate (bossbot) cogs, light on legal.
    # All cogs are level 5..7.
    5101: (BR_TIER + 1, Start, (CogQuest, ToontownGlobals.TheBrrrgh, 25, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5102: (BR_TIER + 1, Start, (CogQuest, ToontownGlobals.TheBrrrgh, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5103: (BR_TIER + 1, Start, (CogQuest, ToontownGlobals.TheBrrrgh, 35, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5104: (BR_TIER + 1, Start, (CogQuest, Anywhere, 45, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5105: (BR_TIER + 1, Start, (CogQuest, Anywhere, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5106: (BR_TIER + 1, Start, (CogQuest, Anywhere, 55, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    5108: (BR_TIER + 1, Start, (CogQuest, Anywhere, 16, 'ym'), Any, ToonHQ, Any, NA, DefaultDialog),
    5109: (BR_TIER + 1, Start, (CogQuest, Anywhere, 12, 'mm'), Any, ToonHQ, Any, NA, DefaultDialog),
    5110: (BR_TIER + 1, Start, (CogQuest, Anywhere, 10, 'ds'), Any, ToonHQ, Any, NA, DefaultDialog),
    5111: (BR_TIER + 1, Start, (CogQuest, Anywhere, 8, 'hh'), Any, ToonHQ, Any, NA, DefaultDialog),

    5114: (BR_TIER + 1, Start, (CogQuest, Anywhere, 16, 'nd'), Any, ToonHQ, Any, NA, DefaultDialog),
    5115: (BR_TIER + 1, Start, (CogQuest, Anywhere, 12, 'gh'), Any, ToonHQ, Any, NA, DefaultDialog),
    5116: (BR_TIER + 1, Start, (CogQuest, Anywhere, 10, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),
    5117: (BR_TIER + 1, Start, (CogQuest, Anywhere, 8, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),

    5120: (BR_TIER + 1, Start, (CogQuest, Anywhere, 16, 'tw'), Any, ToonHQ, Any, NA, DefaultDialog),
    5121: (BR_TIER + 1, Start, (CogQuest, Anywhere, 12, 'bc'), Any, ToonHQ, Any, NA, DefaultDialog),
    5122: (BR_TIER + 1, Start, (CogQuest, Anywhere, 10, 'nc'), Any, ToonHQ, Any, NA, DefaultDialog),
    5123: (BR_TIER + 1, Start, (CogQuest, Anywhere, 8, 'mb'), Any, ToonHQ, Any, NA, DefaultDialog),

    5126: (BR_TIER + 1, Start, (CogQuest, Anywhere, 16, 'dt'), Any, ToonHQ, Any, NA, DefaultDialog),
    5127: (BR_TIER + 1, Start, (CogQuest, Anywhere, 12, 'ac'), Any, ToonHQ, Any, NA, DefaultDialog),
    5128: (BR_TIER + 1, Start, (CogQuest, Anywhere, 10, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),
    5129: (BR_TIER + 1, Start, (CogQuest, Anywhere, 8, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),

    5131: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 25, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5132: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 30, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5133: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 35, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    5134: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 6, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5135: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 10, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5136: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 20, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5137: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 2, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5138: (BR_TIER + 1, Start, (CogLevelQuest, Anywhere, 8, 8), Any, ToonHQ, Any, NA, DefaultDialog),

    5139: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 18, 'm'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5140: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 18, 's'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5141: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 18, 'c'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5142: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 18, 'l'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5143: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 24, 'm'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5144: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 24, 's'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5145: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 24, 'c'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5146: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 24, 'l'), Any, ToonHQ, Any, NA,
           DefaultDialog),

    5147: (BR_TIER + 1, Start, (CogTrackQuest, Anywhere, 30, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    5148: (BR_TIER + 1, Start, (CogTrackQuest, Anywhere, 30, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    5149: (BR_TIER + 1, Start, (CogTrackQuest, Anywhere, 30, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    5150: (BR_TIER + 1, Start, (CogTrackQuest, Anywhere, 30, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    5151: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 4, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    5152: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 3, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5153: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5154: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'm', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5155: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 's', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5156: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'c', 4), Any, ToonHQ, Any, NA, DefaultDialog),
    5157: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'l', 4), Any, ToonHQ, Any, NA, DefaultDialog),

    # Lawbot HQ quests
    5160: (BR_TIER + 1, Start, (CogQuest, ToontownGlobals.LawbotHQ, 20, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5161: (BR_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.LawbotHQ, 8, 11), Any, ToonHQ, Any, NA, DefaultDialog),
    5162: (BR_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.LawbotStageIntA, 12, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5163: (BR_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.LawbotStageIntB, 18, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5164: (BR_TIER + 1, Start, (StageQuest, ToontownGlobals.LawbotStageIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5165: (BR_TIER + 1, Start, (StageQuest, ToontownGlobals.LawbotStageIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5166: (BR_TIER + 1, Start, (StageQuest, ToontownGlobals.LawbotStageIntC, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5167: (BR_TIER + 1, Start, (SkelecogQuest, ToontownGlobals.LawbotHQ, 12), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5168: (BR_TIER + 1, Start, (SkelecogLevelQuest, ToontownGlobals.LawbotHQ, 4, 12), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5169: (BR_TIER + 1, Start, (SkelecogLevelQuest, ToontownGlobals.SellbotHQ, 3, 6), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5170: (BR_TIER + 1, Start, (ClerkQuest, ToontownGlobals.LawbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5171: (BR_TIER + 1, Start, (ClerkQuest, ToontownGlobals.LawbotStageIntC, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # A Downsizer stole Chicken Boy's soccer ball.  If you get it back to him
    # your reward is +1 HP.
    5200: (BR_TIER + 1, Start, (VisitQuest,), Any, 3110, NA, (5201, 5261, 5262, 5263),
           TTLocalizer.QuestDialogDict[5200]),
    5201: (BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 3001, VeryHard, 'hh'), 3110, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5201]),
    5261: (BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 3001, VeryHard, 'tf'), 3110, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5261]),
    5262: (BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 3001, VeryHard, 'mb'), 3110, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5262]),
    5263: (BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 3001, VeryHard, 'sd'), 3110, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5263]),

    # Toboggan Ted and his toboggan team crashed while racing and now
    # are a bunch of absent-minded knuckleheads.  Ted sends you to each 
    # team member looking for his large bag.  Each guy has misplaced something
    # that might remind him where the bag is or who another team member is.
    # Your eventual reward is the large bag (max gag = 65).
    5202: (BR_TIER + 1, Start, (VisitQuest,), Any, 3108, NA, 5203,
           TTLocalizer.QuestDialogDict[5202]),
    5203: (
        BR_TIER + 1, Start, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3002, VeryHard, Any), 3108, Same, NA,
        5204,
        TTLocalizer.QuestDialogDict[5203]),
    5204: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3205, NA, 5205,
           TTLocalizer.QuestDialogDict[5204]),
    5205: (
        BR_TIER + 1, Cont, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 3, 3003, Hard, AnyFish), Same, Same, NA,
        5206,
        TTLocalizer.QuestDialogDict[5205]),
    5206: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3210, NA, 5207,
           TTLocalizer.QuestDialogDict[5206]),
    5207: (BR_TIER + 1, Cont, (BuildingQuest, Anywhere, 5, Any, 4), Same, Same, NA, 5208,
           TTLocalizer.QuestDialogDict[5207]),
    5208: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3114, NA, 5209,
           TTLocalizer.QuestDialogDict[5208]),
    5209: (BR_TIER + 1, Cont, (CogLevelQuest, Anywhere, 20, 7), Same, Same, 208, NA,
           TTLocalizer.QuestDialogDict[5209]),

    # Vidalia Va Voom is in love with Snooty Sinjin.  She writes him a love
    # letter, which gets stolen by the Cogs.  Return the letter to Vidalia
    # who will then ask to deliver it to Sinjin.  Sinjin can't be bothered
    # because 10 wiener dogs have gone missing from his kennel.  Once his dogs
    # are returned, he hands over an IOU for an engagement ring.  Deliver the
    # IOU to Creepy Carl, who wants some fish in exchange for producing the
    # ring.  Deliver the ring to Vidalia to get training frame #9.
    5210: (BR_TIER + 1, Start, (VisitQuest,), Any, 3206, NA, (5211, 5264, 5265, 5266),
           TTLocalizer.QuestDialogDict[5210]),
    5211: (
        BR_TIER + 1, Start, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3004, Medium, 'le'), 3206, Same, NA,
        5212,
        TTLocalizer.QuestDialogDict[5211]),
    5264: (
        BR_TIER + 1, Start, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3004, Medium, 'ls'), 3206, Same, NA, 5212,
        TTLocalizer.QuestDialogDict[5264]),
    5265: (
        BR_TIER + 1, Start, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3004, Medium, 'm'), 3206, Same, NA, 5212,
        TTLocalizer.QuestDialogDict[5265]),
    5266: (
        BR_TIER + 1, Start, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3004, Medium, 'cr'), 3206, Same, NA, 5212,
        TTLocalizer.QuestDialogDict[5266]),
    5212: (BR_TIER + 1, Cont, (DeliverItemQuest, 3004), Same, 3111, NA, 5213,
           TTLocalizer.QuestDialogDict[5212]),
    5213: (
        BR_TIER + 1, Cont, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 8, 3005, Hard, Any), Same, Same, NA, 5214,
        TTLocalizer.QuestDialogDict[5213]),
    5214: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3119, NA, 5215,
           TTLocalizer.QuestDialogDict[5214]),
    5215: (BR_TIER + 1, Cont, (CogLevelQuest, Anywhere, 5, 9), Same, Same, NA, 5216,
           TTLocalizer.QuestDialogDict[5215]),
    5216: (BR_TIER + 1, Cont, (DeliverItemQuest, 3006), Same, 3206, 809, NA,
           TTLocalizer.QuestDialogDict[5216]),

    # Hysterical Harry is flipping out.  He asks to help clear out all the
    # Micromanagers, then all the x's, then all the x's, but nothing seems
    # to calm him.  Maybe Fanny Freezes can cook him up a potion to calm him
    # down.  Fanny asks for a series of ingredients and then gives you
    # the concoction to take to Harry.  Harry drinks it and gives you the 
    # max quest = 4.
    5217: (BR_TIER + 1, Start, (VisitQuest,), Any, 3113, NA, 5218,
           TTLocalizer.QuestDialogDict[5217]),
    5218: (BR_TIER + 1, Start, (CogQuest, Anywhere, 10, 'm'), 3113, Same, NA, 5219,
           TTLocalizer.QuestDialogDict[5218]),
    5219: (BR_TIER + 1, Cont, (CogQuest, Anywhere, 10, 'cr'), Same, Same, NA, 5220,
           TTLocalizer.QuestDialogDict[5219]),
    5220: (BR_TIER + 1, Cont, (CogQuest, Anywhere, 10, 'ls'), Same, Same, NA, 5221,
           TTLocalizer.QuestDialogDict[5220]),
    5221: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3211, NA, 5222,
           TTLocalizer.QuestDialogDict[5221]),
    5222: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 2, 3007, Hard, AnyFish), Same, Same, NA, 5223,
           TTLocalizer.QuestDialogDict[5222]),
    5223: (BR_TIER + 1, Cont, (DeliverItemQuest, 3008), Same, 3113, NA, 5224,
           TTLocalizer.QuestDialogDict[5223]),
    5224: (BR_TIER + 1, Cont, (CogQuest, Anywhere, 5, 'le'), Same, Same, 502, NA,
           TTLocalizer.QuestDialogDict[5224]),

    # Gus Gooseburger wants to reconcile with Grumpy Phil, with your help.
    # You see, Gus baked him some turnip bread which caused Grumpy Phil to
    # break a tooth.  Phil has kept the tooth, but if you delivered it to 
    # Dr. Mumbleface he might be able to repair it.  Wacky comedy ensues when
    # Dr. Mumbleface loses the repaired tooth.  Finally, Phil gets his tooth
    # and lightens up on poor Gus.  Gus responds by baking a loaf of pine cone
    # bread, which breaks another one of Phil's teeth.  You reward is 
    # teleport to the Brrrgh.
    5225: (BR_TIER + 1, Start, (VisitQuest,), Any, 3106, NA, 5226,
           TTLocalizer.QuestDialogDict[5225]),
    5226: (BR_TIER + 1, Start, (BuildingQuest, Anywhere, 3, 'm', 4), 3106, Same, NA, 5227,
           TTLocalizer.QuestDialogDict[5226]),
    5227: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3208, NA, 5228,
           TTLocalizer.QuestDialogDict[5227]),
    5228: (BR_TIER + 1, Cont, (DeliverItemQuest, 3009), Same, 3207, NA, (5229, 5267, 5268, 5269),
           TTLocalizer.QuestDialogDict[5228]),
    5229: (BR_TIER + 1, Cont, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 8, 'm'), Same, Same, NA, 5230,
           TTLocalizer.QuestDialogDict[5229]),
    5267: (BR_TIER + 1, Cont, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 8, 's'), Same, Same, NA, 5230,
           TTLocalizer.QuestDialogDict[5267]),
    5268: (BR_TIER + 1, Cont, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 8, 'l'), Same, Same, NA, 5230,
           TTLocalizer.QuestDialogDict[5268]),
    5269: (
        BR_TIER + 1, Cont, (CogTrackQuest, ToontownGlobals.TheBrrrgh, 8, 'c'), Same, Same, NA, (5230, 5270, 5271, 5272),
        TTLocalizer.QuestDialogDict[5269]),
    5230: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3010, Hard, 'rb'), Same, Same, NA, 5231,
           TTLocalizer.QuestDialogDict[5230]),
    5270: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3010, Hard, 'tbc'), Same, Same, NA, 5231,
           TTLocalizer.QuestDialogDict[5270]),
    5271: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3010, Hard, 'mh'), Same, Same, NA, 5231,
           TTLocalizer.QuestDialogDict[5271]),
    5272: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3010, Medium, 'bw'), Same, Same, NA, 5231,
           TTLocalizer.QuestDialogDict[5272]),
    5231: (BR_TIER + 1, Cont, (DeliverItemQuest, 3010), Same, 3208, NA, 5232,
           TTLocalizer.QuestDialogDict[5231]),
    5232: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3106, NA, 5233,
           TTLocalizer.QuestDialogDict[5232]),
    5233: (BR_TIER + 1, Cont, (DeliverItemQuest, 3011), Same, 3208, 304, NA,
           TTLocalizer.QuestDialogDict[5233]),

    # Sweaty Pete needs a shower.  First, he needs a gear from a Micromanager
    # to fix a leaky pipe.  Then he needs the companionship of a rubber ducky,
    # which can be caught in the pond.  Finally, he thinks Cogs are spying
    # on him from nearby buildings while he showers.  The reward for solving his
    # problems is a measly +2 HP.
    5243: (BR_TIER + 1, Start, (VisitQuest,), Any, 3217, NA, 5244,
           TTLocalizer.QuestDialogDict[5243]),
    5244: (BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 2007, VeryHard, 'mm'), 3217, Same, NA, 5245,
           TTLocalizer.QuestDialogDict[5244]),
    5245: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3017, Hard, AnyFish), Same, Same, NA, 5246,
           TTLocalizer.QuestDialogDict[5245]),
    5246: (BR_TIER + 1, Cont, (BuildingQuest, ToontownGlobals.TheBrrrgh, 5, Any, 1), Same, Same, 101, NA,
           # limited to this hood, so no need restricting the number of floors.
           TTLocalizer.QuestDialogDict[5246]),

    # Lounge Lassard was setting up for a gig and the Cogs came in a took
    # his microphone, electronic keyboard, toupee, and platform shoes.  Help
    # him recover these items and he'll reward you with +3 HP
    5251: (BR_TIER + 1, Start, (VisitQuest,), Any, 3134, NA, 5252,
           TTLocalizer.QuestDialogDict[5251]),
    5252: (
        BR_TIER + 1, Start, (RecoverItemQuest, Anywhere, 1, 3019, VeryHard, Any), 3134, Same, NA,
        (5253, 5273, 5274, 5275),
        TTLocalizer.QuestDialogDict[5252]),
    5253: (
        BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3020, VeryHard, "cr"), Same, Same, NA,
        (5254, 5282, 5283, 5284),
        TTLocalizer.QuestDialogDict[5253]),
    5273: (
        BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3020, VeryHard, "m"), Same, Same, NA,
        (5254, 5282, 5283, 5284),
        TTLocalizer.QuestDialogDict[5273]),
    5274: (
        BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3020, VeryHard, "ls"), Same, Same, NA,
        (5254, 5282, 5283, 5284),
        TTLocalizer.QuestDialogDict[5274]),
    5275: (
        BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3020, Hard, "le"), Same, Same, NA, (5254, 5282, 5283, 5284),
        TTLocalizer.QuestDialogDict[5275]),
    5254: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3021, VeryHard, "mh"), Same, Same, 102, NA,
           TTLocalizer.QuestDialogDict[5254]),
    5282: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3021, VeryHard, "tbc"), Same, Same, 102, NA,
           TTLocalizer.QuestDialogDict[5282]),
    5283: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3021, VeryHard, "rb"), Same, Same, 102, NA,
           TTLocalizer.QuestDialogDict[5283]),
    5284: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 1, 3021, Hard, "bw"), Same, Same, 102, NA,
           TTLocalizer.QuestDialogDict[5284]),

    # Wynne Chill wants to trade.  If you wipe out cogs for her, she'll 
    # give you +1 HP. 
    5255: (BR_TIER + 1, Start, (VisitQuest,), Any, 3228, NA, (5256, 5276),
           TTLocalizer.QuestDialogDict[5255]),
    5256: (BR_TIER + 1, Cont, (CogTrackQuest, Anywhere, 45, 'c'), 3228, Same, NA, (5257, 5277),
           TTLocalizer.QuestDialogDict[5256]),
    5276: (BR_TIER + 1, Cont, (CogTrackQuest, Anywhere, 40, 'l'), 3228, Same, NA, (5257, 5277),
           TTLocalizer.QuestDialogDict[5276]),
    5257: (BR_TIER + 1, Cont, (CogTrackQuest, Anywhere, 45, 's'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5257]),
    5277: (BR_TIER + 1, Cont, (CogTrackQuest, Anywhere, 45, 'm'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5277]),

    # Go see Eddie the Yeti. If you kill some lawbots he'll give you +1 laff.
    5301: (BR_TIER + 1, Start, (VisitQuest,), Any, 3304, NA, 5302,
           TTLocalizer.QuestDialogDict[5301]),
    5302: (BR_TIER + 1, Cont, (CogTrackQuest, Anywhere, 90, 'l'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[5302]),

    # Johnny Cashmere is missing several knitting supplies for making sweaters. Help him recover them all
    # and he will knit you a large bag (max gag = 50).
    5303: (BR_TIER + 1, Start, (VisitQuest,), Any, 3318, NA, 5304,
           TTLocalizer.QuestDialogDict[5303]),
    5304: (
        BR_TIER + 1, Cont, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 1, 3024, VeryHard, 'l', 'track'), Same, Same,
        NA,
        5305,
        TTLocalizer.QuestDialogDict[5304]),
    5305: (BR_TIER + 1, Cont, (CogLevelQuest, Anywhere, 20, 7), Same, Same, NA, 5306,
           TTLocalizer.QuestDialogDict[5305]),
    5306: (
        BR_TIER + 1, Cont, (RecoverItemQuest, ToontownGlobals.TheBrrrgh, 2, 3025, Hard, AnyFish), Same, Same, NA,
        5307,
        TTLocalizer.QuestDialogDict[5306]),
    5307: (BR_TIER + 1, Cont, (BuildingQuest, Anywhere, 5, Any, 4), Same, Same, 204, NA,
           TTLocalizer.QuestDialogDict[5307]),

    # March Harry is scared the Lawbots are going to sue him. He asks you to take out several
    # of them on his street. When this doesn't appease him he sends you too Hysterical Harry
    # to get an alibi for him. When you return with it, he rewards you with max quest = 4.
    5308: (BR_TIER + 1, Start, (VisitQuest,), Any, 3312, NA, 5309, TTLocalizer.QuestDialogDict[5308]),
    5309: (BR_TIER + 1, Start, (CogTrackQuest, ToontownGlobals.PolarPlace, 30, 'l'), Same, Same, NA, 5310,
           TTLocalizer.QuestDialogDict[5309]),
    5310: (BR_TIER + 1, Cont, (VisitQuest,), Same, 3113, NA, 5311,
           TTLocalizer.QuestDialogDict[5310]),
    5311: (BR_TIER + 1, Cont, (RecoverItemQuest, Anywhere, 2, 3026, Medium, 'le'), Same, Same, NA, 5312,
           TTLocalizer.QuestDialogDict[5311]),
    5312: (BR_TIER + 1, Cont, (DeliverItemQuest, 3026), Same, 3312, 502, NA,
           TTLocalizer.QuestDialogDict[5312]),

    # Professor Flake wants to research the temperature difference inside and outside Lawbot HQ.
    # Defeat some Polar Place cogs, and then some Lawbot HQ cogs.
    # Turn in the report to Professor Pete. Reward: max carry = 70
    5313: (BR_TIER + 2, Start, (VisitQuest,), Any, 3310, NA, 5314, TTLocalizer.QuestDialogDict[5313]),
    5314: (BR_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.PolarPlace, 5, 3027, Hard, Any), Same, Same, NA, 5315,
           TTLocalizer.QuestDialogDict[5314]),
    5315: (BR_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.LawbotHQ, 15, 3027, Easy, Any), Same, Same, NA, 5316,
           TTLocalizer.QuestDialogDict[5315]),
    5316: (BR_TIER + 2, Cont, (DeliverItemQuest, 1304), Any, 2003, 209, NA, DefaultDialog),

    # It's time for the final challenge.  Return to Lil Oldman for him to
    # review your progress.  Before you can begin, you must eat, Oldman asks 
    # for lumpy cheese from Big Cheeses to put in your broth.  Then he discovers
    # his spoon is missing - maybe a Big Wig took it?  Next, Oldman
    # sends you to catch a talking toad from the pond.  The toad whispers
    # something you can't catch, which prompts Oldman to send you out for
    # dessert, maybe popsicles?  It turns out the popsicles were carted off 
    # by a bunch of high level corporate Cogs, so you've got to track them 
    # down.  Finally, Oldman and his toad get their popsicles, and you get
    # your new track.
    903: (BR_TIER + 2, Start, (VisitQuest,), Any, 3112, NA, (5234, 5278),
          TTLocalizer.QuestDialogDict[903]),
    5234: (BR_TIER + 2, Start, (RecoverItemQuest, Anywhere, 4, 3012, Easy, 'tbc'), 3112, Same, NA, 5235,
           TTLocalizer.QuestDialogDict[5234]),
    5278: (BR_TIER + 2, Start, (RecoverItemQuest, Anywhere, 4, 3022, Easy, 'mh'), 3112, Same, NA, 5235,
           TTLocalizer.QuestDialogDict[5278]),
    5235: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 3013, Medium, 'bw'), Same, Same, NA, 5236,
           TTLocalizer.QuestDialogDict[5279]),
    5236: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 3014, Hard, AnyFish), Same, Same, NA, 5237,
           TTLocalizer.QuestDialogDict[5236]),
    5237: (BR_TIER + 2, Cont, (VisitQuest,), Same, 3128, NA, (5238, 5280),
           TTLocalizer.QuestDialogDict[5237]),
    5238: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 6, 3015, VeryEasy, 'mh'), Same, Same, NA, 5239,
           TTLocalizer.QuestDialogDict[5238]),
    5280: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 6, 3015, VeryEasy, 'tbc'), Same, Same, NA, 5239,
           TTLocalizer.QuestDialogDict[5280]),
    5239: (BR_TIER + 2, Cont, (DeliverItemQuest, 3015), Same, 3112, NA, 5240,
           TTLocalizer.QuestDialogDict[5239]),
    5240: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 3016, Hard, 'bw'), Same, Same, NA, 5241,
           TTLocalizer.QuestDialogDict[5240]),
    5241: (BR_TIER + 2, Cont, (CJQuest, ToontownGlobals.LawbotHQ, 1), Same, Same, NA, 5242,
           TTLocalizer.QuestDialogDict[5241]),
    5242: (BR_TIER + 2, Cont, (RecoverItemQuest, Anywhere, 1, 3014, VeryHard, AnyFish), Same, Same, 810, NA,
           TTLocalizer.QuestDialogDict[5242]),

    # Optional quests to do while working on the bottleneck quest
    5320: (BR_TIER + 2, Start, (CogQuest, Anywhere, 36, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5321: (BR_TIER + 2, Start, (CogQuest, Anywhere, 38, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5322: (BR_TIER + 2, Start, (CogQuest, Anywhere, 40, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5323: (BR_TIER + 2, Start, (CogQuest, Anywhere, 42, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5324: (BR_TIER + 2, Start, (CogQuest, Anywhere, 44, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5325: (BR_TIER + 2, Start, (CogQuest, Anywhere, 46, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5326: (BR_TIER + 2, Start, (CogQuest, Anywhere, 48, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5327: (BR_TIER + 2, Start, (CogQuest, Anywhere, 53, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5328: (BR_TIER + 2, Start, (CogQuest, Anywhere, 52, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5329: (BR_TIER + 2, Start, (CogQuest, Anywhere, 54, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5330: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 25, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5331: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 30, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    5332: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 35, 6), Any, ToonHQ, Any, NA, DefaultDialog),
    5333: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 6, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5334: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 10, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5335: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    5336: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 2, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5337: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 8, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5338: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 10, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    5339: (BR_TIER + 2, Start, (CogLevelQuest, Anywhere, 12, 8), Any, ToonHQ, Any, NA, DefaultDialog),

    # Sellbot HQ quests
    5371: (BR_TIER + 2, Start, (CogQuest, ToontownGlobals.SellbotHQ, 25, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5372: (BR_TIER + 2, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5373: (BR_TIER + 2, Start, (SkelecogQuest, ToontownGlobals.SellbotFactoryInt, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5374: (BR_TIER + 2, Start, (ForemanQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # Cashbot HQ quests
    5381: (BR_TIER + 2, Start, (CogQuest, ToontownGlobals.CashbotHQ, 25, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5382: (BR_TIER + 2, Start, (MintQuest, ToontownGlobals.CashbotMintIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5383: (BR_TIER + 2, Start, (SkelecogQuest, ToontownGlobals.CashbotMintIntA, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5384: (BR_TIER + 2, Start, (SupervisorQuest, ToontownGlobals.CashbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # Lawbot HQ quests
    5391: (BR_TIER + 2, Start, (CogQuest, ToontownGlobals.LawbotHQ, 20, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    5392: (BR_TIER + 2, Start, (StageQuest, ToontownGlobals.LawbotStageIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    5393: (BR_TIER + 2, Start, (SkelecogQuest, ToontownGlobals.LawbotStageIntA, 10), Any, ToonHQ, Any, NA,
           DefaultDialog),
    5394: (BR_TIER + 2, Start, (ClerkQuest, ToontownGlobals.LawbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    # Dreamland
    # Cogs in DL are well-balanced.  Levels are 5..9.
    6101: (DL_TIER, Start, (CogQuest, ToontownGlobals.DonaldsDreamland, 20, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    6102: (DL_TIER, Start, (CogQuest, Anywhere, 40, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    6103: (DL_TIER, Start, (CogLevelQuest, Anywhere, 30, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    6104: (DL_TIER, Start, (CogLevelQuest, Anywhere, 25, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    6105: (DL_TIER, Start, (CogLevelQuest, Anywhere, 15, 9), Any, ToonHQ, Any, NA, DefaultDialog),

    6111: (DL_TIER, Start, (CogQuest, Anywhere, 10, 'ds'), Any, ToonHQ, Any, NA, DefaultDialog),
    6112: (DL_TIER, Start, (CogQuest, Anywhere, 7, 'hh'), Any, ToonHQ, Any, NA, DefaultDialog),
    6113: (DL_TIER, Start, (CogQuest, Anywhere, 3, 'cr'), Any, ToonHQ, Any, NA, DefaultDialog),

    6114: (DL_TIER, Start, (CogQuest, Anywhere, 10, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),
    6115: (DL_TIER, Start, (CogQuest, Anywhere, 7, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),
    6116: (DL_TIER, Start, (CogQuest, Anywhere, 4, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),

    6117: (DL_TIER, Start, (CogQuest, Anywhere, 10, 'nc'), Any, ToonHQ, Any, NA, DefaultDialog),
    6118: (DL_TIER, Start, (CogQuest, Anywhere, 7, 'mb'), Any, ToonHQ, Any, NA, DefaultDialog),
    6119: (DL_TIER, Start, (CogQuest, Anywhere, 4, 'ls'), Any, ToonHQ, Any, NA, DefaultDialog),

    6120: (DL_TIER, Start, (CogQuest, Anywhere, 10, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),
    6121: (DL_TIER, Start, (CogQuest, Anywhere, 7, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),
    6122: (DL_TIER, Start, (CogQuest, Anywhere, 4, 'le'), Any, ToonHQ, Any, NA, DefaultDialog),

    6131: (DL_TIER, Start, (CogTrackQuest, ToontownGlobals.DonaldsDreamland, 12, 'm'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6132: (DL_TIER, Start, (CogTrackQuest, ToontownGlobals.DonaldsDreamland, 12, 's'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6133: (DL_TIER, Start, (CogTrackQuest, ToontownGlobals.DonaldsDreamland, 12, 'c'), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6134: (DL_TIER, Start, (CogTrackQuest, ToontownGlobals.DonaldsDreamland, 12, 'l'), Any, ToonHQ, Any, NA,
           DefaultDialog),

    6135: (DL_TIER, Start, (CogTrackQuest, Anywhere, 24, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    6136: (DL_TIER, Start, (CogTrackQuest, Anywhere, 24, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    6137: (DL_TIER, Start, (CogTrackQuest, Anywhere, 24, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    6138: (DL_TIER, Start, (CogTrackQuest, Anywhere, 24, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    6151: (DL_TIER, Start, (BuildingQuest, Anywhere, 5, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    6152: (DL_TIER, Start, (BuildingQuest, Anywhere, 4, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    6153: (DL_TIER, Start, (BuildingQuest, Anywhere, 2, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    6154: (DL_TIER, Start, (BuildingQuest, Anywhere, 1, Any, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    6155: (DL_TIER, Start, (BuildingQuest, Anywhere, 1, 'm', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    6156: (DL_TIER, Start, (BuildingQuest, Anywhere, 1, 's', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    6157: (DL_TIER, Start, (BuildingQuest, Anywhere, 1, 'c', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    6158: (DL_TIER, Start, (BuildingQuest, Anywhere, 1, 'l', 5), Any, ToonHQ, Any, NA, DefaultDialog),

    # ID: 6160 - 6199 available

    # Powers Erge, though forgetful, will give you an LP boost
    # if you'll defeat some Cogs for him
    6201: (DL_TIER, Start, (VisitQuest,), Any, 9111, NA, 6202, TTLocalizer.QuestDialogDict[6201]),
    6202: (DL_TIER, Start, (CogQuest, ToontownGlobals.DonaldsDreamland, 25, Any), 9111, Same, 100, NA,
           TTLocalizer.QuestDialogDict[6202]),

    # Susan Siesta wants to get rich but the Cogs are interfering.
    # Take out some Cog buildings and she'll give you the 70 gag pouch
    6206: (DL_TIER, Start, (VisitQuest,), Any, 9131, NA, 6207, TTLocalizer.QuestDialogDict[6206]),
    6207: (DL_TIER, Start, (BuildingQuest, ToontownGlobals.DonaldsDreamland, 4, Any, 4), 9131, Same, 210, NA,
           TTLocalizer.QuestDialogDict[6207]),

    # Lawful Linda is fixing her answering machine.
    # Help her & she'll give you a 1LP reward.
    6211: (DL_TIER, Start, (VisitQuest,), Any, 9217, NA, 6212, TTLocalizer.QuestDialogDict[6211]),
    6212: (DL_TIER, Start, (RecoverItemQuest, Anywhere, 1, 6002, Medium, 'bc'), 9217, Same, NA, 6213,
           TTLocalizer.QuestDialogDict[6212]),
    6213: (DL_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 6003, Medium, 'mb'), Same, Same, NA, 6214,
           TTLocalizer.QuestDialogDict[6213]),
    6214: (DL_TIER, Cont, (RecoverItemQuest, Anywhere, 1, 6004, Medium, 'pp'), Same, Same, 100, NA,
           TTLocalizer.QuestDialogDict[6214]),

    # Scratch Rocco's back and he'll scratch yours.
    # In fact, he'll give you a 1 LP bonus.
    6221: (DL_TIER, Start, (VisitQuest,), Any, 9119, NA, 6222, TTLocalizer.QuestDialogDict[6221]),
    6222: (DL_TIER, Start, (CogTrackQuest, Any, 25, 'c'), 9119, Same, 100, NA, TTLocalizer.QuestDialogDict[6222]),

    # Nat & PJ want you to tackle one of the headquarters.  Reward is 2 LP
    6231: (DL_TIER, Start, (VisitQuest,), Any, 9203, NA, 6232, TTLocalizer.QuestDialogDict[6231]),
    6232: (DL_TIER, Start, (VisitQuest,), 9203, 9103, NA, (6233, 6234, 6235, 6236), TTLocalizer.QuestDialogDict[6232]),
    6233: (DL_TIER, Cont, (VPQuest, ToontownGlobals.SellbotHQ, 1), Same, Same, NA, 6237,
           TTLocalizer.QuestDialogDict[6233]),
    6234: (DL_TIER, Cont, (MintQuest, ToontownGlobals.CashbotMintIntC, 1), Same, Same, NA, 6237,
           TTLocalizer.QuestDialogDict[6234]),
    6235: (DL_TIER, Cont, (StageQuest, ToontownGlobals.LawbotStageIntB, 1), Same, Same, NA, 6237,
           TTLocalizer.QuestDialogDict[6235]),
    6236: (DL_TIER, Cont, (ClubQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Same, Same, NA, 6237,
           TTLocalizer.QuestDialogDict[6236]),
    6237: (DL_TIER, Cont, (VisitQuest,), Same, Same, 101, NA, TTLocalizer.QuestDialogDict[6237]),

    # The Countess can't concentrate on counting her sheep with all 
    # these Cogs around. Clean up a bit and she'll reward you handsomely.
    # Reward: 1LP
    6241: (DL_TIER, Start, (VisitQuest,), Any, 9219, NA, 6242, TTLocalizer.QuestDialogDict[6241]),
    6242: (DL_TIER, Start, (CogQuest, ToontownGlobals.DonaldsDreamland, 10, 'nc'), 9219, Same, 100, NA,
           TTLocalizer.QuestDialogDict[6242]),

    # Zari needs you to run some errands for her and maybe
    # wipe out some Cogs along the way. She'll make it worthwhile
    # though, she'll give you 4 LP if you run the gauntlet.
    6251: (DL_TIER, Start, (VisitQuest,), Any, 9221, NA, 6252, TTLocalizer.QuestDialogDict[6251]),
    6252: (DL_TIER, Start, (DeliverItemQuest, 6006), 9221, 9222, NA, 6253, TTLocalizer.QuestDialogDict[6252]),
    6253: (DL_TIER, Cont, (VisitQuest,), Same, 9221, NA, 6254, TTLocalizer.QuestDialogDict[6253]),
    6254: (DL_TIER, Cont, (DeliverItemQuest, 6007), Same, 9210, NA, 6255, TTLocalizer.QuestDialogDict[6254]),
    6255: (DL_TIER, Cont, (CogTrackQuest, Anywhere, 70, 'm'), Same, Same, NA, 6256, TTLocalizer.QuestDialogDict[6255]),
    6256: (DL_TIER, Cont, (VisitQuest,), Same, 9221, NA, 6257, TTLocalizer.QuestDialogDict[6256]),
    6257: (DL_TIER, Cont, (DeliverItemQuest, 6008), Same, 9205, NA, 6258, TTLocalizer.QuestDialogDict[6257]),
    6258: (DL_TIER, Cont, (CogQuest, Anywhere, 25, 'ms'), Same, Same, NA, 6259, TTLocalizer.QuestDialogDict[6258]),
    6259: (DL_TIER, Cont, (VisitQuest,), Same, 9221, NA, 6260, TTLocalizer.QuestDialogDict[6259]),
    6260: (DL_TIER, Cont, (DeliverItemQuest, 6009), Same, 9229, NA, 6261, TTLocalizer.QuestDialogDict[6260]),
    6261: (DL_TIER, Cont, (VisitQuest,), Same, 9221, NA, 6262, TTLocalizer.QuestDialogDict[6261]),
    6262: (DL_TIER, Cont, (DeliverItemQuest, 6010), Same, 9126, NA, 6263, TTLocalizer.QuestDialogDict[6262]),
    6263: (DL_TIER, Cont, (DeliverItemQuest, 6010), Same, 9112, NA, 6264, TTLocalizer.QuestDialogDict[6263]),
    6264: (DL_TIER, Cont, (DeliverItemQuest, 6011), Same, 9221, NA, 6265, TTLocalizer.QuestDialogDict[6264]),
    6265: (DL_TIER, Cont, (DeliverItemQuest, 6012), Same, 9115, NA, 6266, TTLocalizer.QuestDialogDict[6265]),
    6266: (DL_TIER, Cont, (VisitQuest,), Same, 9221, 103, NA, TTLocalizer.QuestDialogDict[6266]),

    # Drowsy Dave will give you teleport access to DL
    # if he can stay awake long enough for you to finish.
    6271: (DL_TIER, Start, (VisitQuest,), Any, 9208, NA, 6272, TTLocalizer.QuestDialogDict[6271]),
    6272: (DL_TIER, Start, (BuildingQuest, ToontownGlobals.DonaldsDreamland, 2, 'm', 5), 9208, Same, 305, NA,
           TTLocalizer.QuestDialogDict[6272]),

    # Teddy Blair can't stand noise cogs make. Of course, his ear plugs make it tough.
    # Reward is 1 LP
    6281: (DL_TIER, Start, (VisitQuest,), Any, 9123, NA, 6282, TTLocalizer.QuestDialogDict[6281]),
    6282: (DL_TIER, Start, (CogTrackQuest, ToontownGlobals.DonaldsDreamland, 10, 'm'), 9123, Same, 100, NA,
           TTLocalizer.QuestDialogDict[6282]),

    # William Teller needs help! Those darn cogs swiped his reading lamp!
    # Retrieve it and he'll give you 1 LP
    6291: (DL_TIER, Start, (VisitQuest,), Any, 9226, NA, 6292, TTLocalizer.QuestDialogDict[6291]),
    6292: (DL_TIER, Start, (RecoverItemQuest, ToontownGlobals.DonaldsDreamland, 1, 6005, VeryHard, Any, 'track'), 9226,
           Same,
           100, NA, TTLocalizer.QuestDialogDict[6292]),

    # Bossbot HQ quests
    6303: (DL_TIER, Start, (CogQuest, ToontownGlobals.BossbotHQ, 16, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    6307: (DL_TIER, Start, (CogLevelQuest, ToontownGlobals.BossbotCountryClubIntA, 6, 11), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6308: (DL_TIER, Start, (CogLevelQuest, ToontownGlobals.BossbotCountryClubIntB, 12, 11), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6310: (DL_TIER, Start, (MintQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    6311: (DL_TIER, Start, (MintQuest, ToontownGlobals.BossbotCountryClubIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    6313: (DL_TIER, Start, (SkelecogQuest, ToontownGlobals.BossbotHQ, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    6318: (DL_TIER, Start, (SupervisorQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    6319: (DL_TIER, Start, (SupervisorQuest, ToontownGlobals.BossbotCountryClubIntB, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),

    # Post Dreamland 1
    7101: (DL_TIER + 1, Start, (CogQuest, Anywhere, 40, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7102: (DL_TIER + 1, Start, (CogQuest, Anywhere, 45, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7103: (DL_TIER + 1, Start, (CogQuest, Anywhere, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7104: (DL_TIER + 1, Start, (CogQuest, Anywhere, 55, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7105: (DL_TIER + 1, Start, (CogQuest, Anywhere, 60, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7106: (DL_TIER + 1, Start, (CogQuest, Anywhere, 70, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    7107: (DL_TIER + 1, Start, (CogQuest, Anywhere, 10, 'ds'), Any, ToonHQ, Any, NA, DefaultDialog),
    7108: (DL_TIER + 1, Start, (CogQuest, Anywhere, 8, 'hh'), Any, ToonHQ, Any, NA, DefaultDialog),
    7109: (DL_TIER + 1, Start, (CogQuest, Anywhere, 5, 'cr'), Any, ToonHQ, Any, NA, DefaultDialog),
    7110: (DL_TIER + 1, Start, (CogQuest, Anywhere, 2, 'tbc'), Any, ToonHQ, Any, NA, DefaultDialog),

    7111: (DL_TIER + 1, Start, (CogQuest, Anywhere, 10, 'ms'), Any, ToonHQ, Any, NA, DefaultDialog),
    7112: (DL_TIER + 1, Start, (CogQuest, Anywhere, 8, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),
    7113: (DL_TIER + 1, Start, (CogQuest, Anywhere, 5, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    7114: (DL_TIER + 1, Start, (CogQuest, Anywhere, 2, 'mh'), Any, ToonHQ, Any, NA, DefaultDialog),

    7115: (DL_TIER + 1, Start, (CogQuest, Anywhere, 10, 'nc'), Any, ToonHQ, Any, NA, DefaultDialog),
    7116: (DL_TIER + 1, Start, (CogQuest, Anywhere, 8, 'mb'), Any, ToonHQ, Any, NA, DefaultDialog),
    7117: (DL_TIER + 1, Start, (CogQuest, Anywhere, 5, 'ls'), Any, ToonHQ, Any, NA, DefaultDialog),
    7118: (DL_TIER + 1, Start, (CogQuest, Anywhere, 2, 'rb'), Any, ToonHQ, Any, NA, DefaultDialog),

    7119: (DL_TIER + 1, Start, (CogQuest, Anywhere, 10, 'bs'), Any, ToonHQ, Any, NA, DefaultDialog),
    7120: (DL_TIER + 1, Start, (CogQuest, Anywhere, 8, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),
    7121: (DL_TIER + 1, Start, (CogQuest, Anywhere, 5, 'le'), Any, ToonHQ, Any, NA, DefaultDialog),
    7122: (DL_TIER + 1, Start, (CogQuest, Anywhere, 2, 'bw'), Any, ToonHQ, Any, NA, DefaultDialog),

    7131: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 40, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    7132: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 30, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    7133: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 25, 9), Any, ToonHQ, Any, NA, DefaultDialog),
    7134: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 20, 9), Any, ToonHQ, Any, NA, DefaultDialog),
    7135: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 20, 10), Any, ToonHQ, Any, NA, DefaultDialog),
    7136: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 15, 10), Any, ToonHQ, Any, NA, DefaultDialog),
    7137: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 15, 11), Any, ToonHQ, Any, NA, DefaultDialog),
    7138: (DL_TIER + 1, Start, (CogLevelQuest, Anywhere, 10, 11), Any, ToonHQ, Any, NA, DefaultDialog),

    7139: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 40, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    7140: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 40, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    7141: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 40, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    7142: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 40, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    7143: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 45, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    7144: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 45, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    7145: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 45, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    7146: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 45, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    7147: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 50, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    7148: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 50, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    7149: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 50, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    7150: (DL_TIER + 1, Start, (CogTrackQuest, Anywhere, 50, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    7151: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 4, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    7152: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 4, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    7153: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    7154: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 2, Any, 5), Any, ToonHQ, Any, NA, DefaultDialog),

    7155: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'm', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    7156: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 's', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    7157: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'c', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    7158: (DL_TIER + 1, Start, (BuildingQuest, Anywhere, 1, 'l', 5), Any, ToonHQ, Any, NA, DefaultDialog),

    # ID: 7160 - 7199 available

    # Get Nina Nightlight another bed for her stock 
    # and she'll give you +2 Laff
    7201: (DL_TIER + 1, Start, (VisitQuest,), Any, 9124, NA, 7202, TTLocalizer.QuestDialogDict[7201]),
    7202: (DL_TIER + 1, Start, (VisitQuest,), 9124, 9128, NA, 7203, TTLocalizer.QuestDialogDict[7202]),
    7203: (DL_TIER + 1, Cont, (DeliverItemQuest, 7001), Same, 9124, NA, 7204, TTLocalizer.QuestDialogDict[7203]),
    7204: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9128, NA, 7205, TTLocalizer.QuestDialogDict[7204]),
    7205: (DL_TIER + 1, Cont, (CogQuest, ToontownGlobals.DonaldsDreamland, 20, Any), Same, Same, NA, 7206,
           TTLocalizer.QuestDialogDict[7205]),
    7206: (DL_TIER + 1, Cont, (DeliverItemQuest, 7002), Same, 9124, 101, NA, TTLocalizer.QuestDialogDict[7206]),

    # Help Honey Moon get a new bedspread from Ed for +2 Laff
    7209: (DL_TIER + 1, Start, (VisitQuest,), Any, 9232, NA, 7210, TTLocalizer.QuestDialogDict[7209]),
    7210: (DL_TIER + 1, Start, (VisitQuest,), 9232, 9101, NA, 7211, TTLocalizer.QuestDialogDict[7210]),
    7211: (DL_TIER + 1, Cont, (CogQuest, Anywhere, 6, 'nc'), Same, Same, NA, 7212, TTLocalizer.QuestDialogDict[7211]),
    7212: (DL_TIER + 1, Cont, (DeliverItemQuest, 7003), Same, 9232, NA, 7213, TTLocalizer.QuestDialogDict[7212]),
    7213: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9101, NA, 7214, TTLocalizer.QuestDialogDict[7213]),
    7214: (DL_TIER + 1, Cont, (CogTrackQuest, Anywhere, 15, 'm'), Same, Same, NA, 7215,
           TTLocalizer.QuestDialogDict[7214]),
    7215: (DL_TIER + 1, Cont, (DeliverItemQuest, 7004), Same, 9232, 101, NA, TTLocalizer.QuestDialogDict[7215]),

    # Dreamy Daphne had her pillows stolen but Tex 
    # can help her out. You'll get +3 Laff
    7218: (DL_TIER + 1, Start, (VisitQuest,), Any, 9109, NA, 7219, TTLocalizer.QuestDialogDict[7218]),
    7219: (DL_TIER + 1, Start, (VisitQuest,), 9109, 9230, NA, 7220, TTLocalizer.QuestDialogDict[7219]),
    7220: (DL_TIER + 1, Cont, (DeliverItemQuest, 7005), Same, 9109, NA, 7221, TTLocalizer.QuestDialogDict[7220]),
    7221: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9230, NA, 7222, TTLocalizer.QuestDialogDict[7221]),
    7222: (DL_TIER + 1, Cont, (BuildingQuest, Anywhere, 4, Any, 3), Same, Same, NA, 7223,
           TTLocalizer.QuestDialogDict[7222]),
    7223: (DL_TIER + 1, Cont, (DeliverItemQuest, 7006), Same, 9109, 102, NA, TTLocalizer.QuestDialogDict[7223]),

    # Sandy Sandman lost her pajamas but Big Mama
    # and Cat can help her out. If you hang in there, you'll get max 80 carry
    7226: (DL_TIER + 1, Start, (VisitQuest,), Any, 9224, NA, 7227, TTLocalizer.QuestDialogDict[7226]),
    7227: (DL_TIER + 1, Start, (VisitQuest,), 9224, 9102, NA, 7228, TTLocalizer.QuestDialogDict[7227]),
    7228: (DL_TIER + 1, Cont, (DeliverItemQuest, 7007), Same, 9224, NA, 7229, TTLocalizer.QuestDialogDict[7228]),
    7229: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9102, NA, 7230, TTLocalizer.QuestDialogDict[7229]),
    7230: (DL_TIER + 1, Cont, (DeliverItemQuest, 7008), Same, 9224, NA, 7231, TTLocalizer.QuestDialogDict[7230]),
    7231: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9102, NA, 7232, TTLocalizer.QuestDialogDict[7231]),
    7232: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9216, NA, 7233, TTLocalizer.QuestDialogDict[7232]),
    7233: (DL_TIER + 1, Cont, (DeliverItemQuest, 7009), Same, 9224, NA, 7234, TTLocalizer.QuestDialogDict[7233]),
    7234: (DL_TIER + 1, Cont, (VisitQuest,), Same, 9216, NA, 7235, TTLocalizer.QuestDialogDict[7234]),
    7235: (DL_TIER + 1, Cont, (BuildingQuest, Anywhere, 1, 'm', 5), Same, Same, NA, 7236,
           TTLocalizer.QuestDialogDict[7235]),
    7236: (DL_TIER + 1, Cont, (DeliverItemQuest, 7010), Same, 9224, 211, NA, TTLocalizer.QuestDialogDict[7236]),

    # Bossbot HQ quests
    7250: (DL_TIER + 1, Start, (CogQuest, ToontownGlobals.BossbotHQ, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    7254: (DL_TIER + 1, Start, (CogLevelQuest, ToontownGlobals.BossbotHQ, 20, 10), Any, ToonHQ, Any, NA, DefaultDialog),
    7259: (DL_TIER + 1, Start, (ClubQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    7260: (DL_TIER + 1, Start, (ClubQuest, ToontownGlobals.BossbotCountryClubIntB, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    7262: (DL_TIER + 1, Start, (SkelecogQuest, ToontownGlobals.BossbotHQ, 16), Any, ToonHQ, Any, NA, DefaultDialog),
    7265: (DL_TIER + 1, Start, (PresidentQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    7266: (DL_TIER + 1, Start, (PresidentQuest, ToontownGlobals.BossbotCountryClubIntB, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),

    # Post Dreamland 2
    8101: (DL_TIER + 2, Start, (CogQuest, Anywhere, 30, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    8102: (DL_TIER + 2, Start, (CogQuest, Anywhere, 45, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    8103: (DL_TIER + 2, Start, (CogQuest, Anywhere, 60, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    8110: (DL_TIER + 2, Start, (FactoryQuest, ToontownGlobals.SellbotFactoryInt, 2), Any, ToonHQ, Any, NA,
           DefaultDialog),

    8111: (DL_TIER + 2, Start, (MintQuest, ToontownGlobals.CashbotMintIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    8112: (DL_TIER + 2, Start, (MintQuest, ToontownGlobals.CashbotMintIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    8113: (DL_TIER + 2, Start, (MintQuest, ToontownGlobals.CashbotMintIntC, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    8114: (DL_TIER + 2, Start, (StageQuest, ToontownGlobals.LawbotStageIntA, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    8115: (DL_TIER + 2, Start, (StageQuest, ToontownGlobals.LawbotStageIntB, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    8116: (DL_TIER + 2, Start, (StageQuest, ToontownGlobals.LawbotStageIntC, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    8117: (DL_TIER + 2, Start, (ClubQuest, ToontownGlobals.BossbotCountryClubIntA, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    8118: (DL_TIER + 2, Start, (ClubQuest, ToontownGlobals.BossbotCountryClubIntB, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),
    8119: (DL_TIER + 2, Start, (ClubQuest, ToontownGlobals.BossbotCountryClubIntC, 1), Any, ToonHQ, Any, NA,
           DefaultDialog),

    8120: (DL_TIER + 2, Start, (VPQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),
    8121: (DL_TIER + 2, Start, (CFOQuest, ToontownGlobals.CashbotHQ, 1), Any, ToonHQ, Any, NA, DefaultDialog),

    8130: (DL_TIER + 2, Start, (CogLevelQuest, Anywhere, 20, 9), Any, ToonHQ, Any, NA, DefaultDialog),
    8131: (DL_TIER + 2, Start, (CogLevelQuest, Anywhere, 15, 10), Any, ToonHQ, Any, NA, DefaultDialog),
    8132: (DL_TIER + 2, Start, (CogLevelQuest, Anywhere, 10, 11), Any, ToonHQ, Any, NA, DefaultDialog),
    8133: (DL_TIER + 2, Start, (CogLevelQuest, Anywhere, 5, 12), Any, ToonHQ, Any, NA, DefaultDialog),

    8140: (DL_TIER + 2, Start, (CogTrackQuest, Anywhere, 35, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    8141: (DL_TIER + 2, Start, (CogTrackQuest, Anywhere, 35, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    8142: (DL_TIER + 2, Start, (CogTrackQuest, Anywhere, 35, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    8143: (DL_TIER + 2, Start, (CogTrackQuest, Anywhere, 35, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    8150: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 8, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    8151: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 5, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    8152: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 3, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    8153: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 2, Any, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    8154: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 1, 'm', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    8155: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 1, 's', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    8156: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 1, 'c', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    8157: (DL_TIER + 2, Start, (BuildingQuest, Anywhere, 1, 'l', 5), Any, ToonHQ, Any, NA, DefaultDialog),

    # Smudgy Mascara needs Wrinkle Cream but
    # is missing ingredients. Help them out and get max 85 carry
    8500: (DL_TIER + 2, Start, (VisitQuest,), Any, 9114, NA, 8501, TTLocalizer.QuestDialogDict[8500]),
    8501: (DL_TIER + 2, Start, (VisitQuest,), 9114, 9215, NA, 8502, TTLocalizer.QuestDialogDict[8501]),
    8502: (DL_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.DonaldsDreamland, 1, 7011, Hard, AnyFish),
           Same, Same, NA, 8503, TTLocalizer.QuestDialogDict[8502]),
    8503: (DL_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.DonaldsDreamland, 1, 7012, VeryHard, AnyFish),
           Same, Same, NA, 8504, TTLocalizer.QuestDialogDict[8503]),
    8504: (DL_TIER + 2, Cont, (RecoverItemQuest, ToontownGlobals.CashbotHQ, 1, 7013, Medium, 'ls'),
           Same, Same, NA, 8505, TTLocalizer.QuestDialogDict[8504]),
    8505: (DL_TIER + 2, Cont, (DeliverItemQuest, 7014), Same, 9114, 212, NA, TTLocalizer.QuestDialogDict[8505]),

    # Join the Toon Resistance! Visit Whispering Willow and take on HQ cogs for Track frame #15
    8510: (DL_TIER + 2, Start, (VisitQuest,), Any, 9228, NA, 8511, TTLocalizer.QuestDialogDict[8510]),
    8511: (DL_TIER + 2, Cont, (FactoryQuest, ToontownGlobals.SellbotFactoryInt, 1), Same, Same, NA, 8512,
           TTLocalizer.QuestDialogDict[8511]),
    8512: (DL_TIER + 2, Cont, (MintQuest, ToontownGlobals.CashbotMintIntC, 1), Same, Same, NA, 8513,
           TTLocalizer.QuestDialogDict[8512]),
    8513: (DL_TIER + 2, Cont, (StageQuest, ToontownGlobals.LawbotStageIntD, 1), Same, Same, NA, 8514,
           TTLocalizer.QuestDialogDict[8513]),
    8514: (DL_TIER + 2, Cont, (ClubQuest, ToontownGlobals.BossbotCountryClubIntC, 1), Same, Same, NA, 8515,
           TTLocalizer.QuestDialogDict[8514]),
    8515: (DL_TIER + 2, Cont, (DeliverItemQuest, 8000), Same, 2001, 811, NA, TTLocalizer.QuestDialogDict[8515]),

    # 8183 - 8999 Available (Used to be OBSOLETE)

    # Post Dreamland 3
    9101: (DL_TIER + 3, Start, (CogQuest, Anywhere, 75, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    9110: (DL_TIER + 3, Start, (CogQuest, Anywhere, 12, 'hh'), Any, ToonHQ, Any, NA, DefaultDialog),
    9111: (DL_TIER + 3, Start, (CogQuest, Anywhere, 9, 'cr'), Any, ToonHQ, Any, NA, DefaultDialog),
    9112: (DL_TIER + 3, Start, (CogQuest, Anywhere, 6, 'tbc'), Any, ToonHQ, Any, NA, DefaultDialog),

    9113: (DL_TIER + 3, Start, (CogQuest, Anywhere, 12, 'tf'), Any, ToonHQ, Any, NA, DefaultDialog),
    9114: (DL_TIER + 3, Start, (CogQuest, Anywhere, 9, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    9115: (DL_TIER + 3, Start, (CogQuest, Anywhere, 6, 'mh'), Any, ToonHQ, Any, NA, DefaultDialog),

    9116: (DL_TIER + 3, Start, (CogQuest, Anywhere, 12, 'mb'), Any, ToonHQ, Any, NA, DefaultDialog),
    9117: (DL_TIER + 3, Start, (CogQuest, Anywhere, 9, 'ls'), Any, ToonHQ, Any, NA, DefaultDialog),
    9118: (DL_TIER + 3, Start, (CogQuest, Anywhere, 6, 'rb'), Any, ToonHQ, Any, NA, DefaultDialog),

    9119: (DL_TIER + 3, Start, (CogQuest, Anywhere, 12, 'sd'), Any, ToonHQ, Any, NA, DefaultDialog),
    9120: (DL_TIER + 3, Start, (CogQuest, Anywhere, 9, 'le'), Any, ToonHQ, Any, NA, DefaultDialog),
    9121: (DL_TIER + 3, Start, (CogQuest, Anywhere, 6, 'bw'), Any, ToonHQ, Any, NA, DefaultDialog),

    9130: (DL_TIER + 3, Start, (CogLevelQuest, Anywhere, 40, 8), Any, ToonHQ, Any, NA, DefaultDialog),
    9131: (DL_TIER + 3, Start, (CogLevelQuest, Anywhere, 20, 10), Any, ToonHQ, Any, NA, DefaultDialog),
    9132: (DL_TIER + 3, Start, (CogLevelQuest, Anywhere, 10, 12), Any, ToonHQ, Any, NA, DefaultDialog),
    9133: (DL_TIER + 3, Start, (CogLevelQuest, Anywhere, 5, 14), Any, ToonHQ, Any, NA, DefaultDialog),

    9140: (DL_TIER + 3, Start, (CogTrackQuest, Anywhere, 40, 'm'), Any, ToonHQ, Any, NA, DefaultDialog),
    9141: (DL_TIER + 3, Start, (CogTrackQuest, Anywhere, 40, 's'), Any, ToonHQ, Any, NA, DefaultDialog),
    9142: (DL_TIER + 3, Start, (CogTrackQuest, Anywhere, 40, 'c'), Any, ToonHQ, Any, NA, DefaultDialog),
    9143: (DL_TIER + 3, Start, (CogTrackQuest, Anywhere, 40, 'l'), Any, ToonHQ, Any, NA, DefaultDialog),

    9150: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 8, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9151: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 5, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    9152: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 4, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    9153: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 2, Any, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    9154: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 1, 'm', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    9155: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 1, 's', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    9156: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 1, 'c', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    9157: (DL_TIER + 3, Start, (BuildingQuest, Anywhere, 1, 'l', 5), Any, ToonHQ, Any, NA, DefaultDialog),

    # Sellbot HQ quests
    9160: (DL_TIER + 3, Start, (CogQuest, ToontownGlobals.SellbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    9161: (DL_TIER + 3, Start, (CogLevelQuest, ToontownGlobals.SellbotHQ, 30, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    9162: (DL_TIER + 3, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9163: (DL_TIER + 3, Start, (SkelecogQuest, ToontownGlobals.SellbotFactoryInt, 12), Any, ToonHQ, Any, NA,
           DefaultDialog),
    9164: (DL_TIER + 3, Start, (ForemanQuest, ToontownGlobals.SellbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9165: (DL_TIER + 3, Start, (VPQuest, ToontownGlobals.SellbotHQ, 1), Any, ToonHQ, 619, NA, DefaultDialog),

    # Cashbot HQ quests
    9170: (DL_TIER + 3, Start, (CogQuest, ToontownGlobals.CashbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    9171: (DL_TIER + 3, Start, (CogLevelQuest, ToontownGlobals.CashbotHQ, 30, 7), Any, ToonHQ, Any, NA, DefaultDialog),
    9172: (DL_TIER + 3, Start, (MintQuest, ToontownGlobals.CashbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9173: (DL_TIER + 3, Start, (SkelecogQuest, ToontownGlobals.CashbotMintIntC, 16), Any, ToonHQ, Any, NA,
           DefaultDialog),
    9174: (DL_TIER + 3, Start, (SupervisorQuest, ToontownGlobals.CashbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9175: (DL_TIER + 3, Start, (CFOQuest, ToontownGlobals.CashbotHQ, 1), Any, ToonHQ, 620, NA, DefaultDialog),

    # Lawbot HQ quests
    9180: (DL_TIER + 3, Start, (CogQuest, ToontownGlobals.LawbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    9181: (DL_TIER + 3, Start, (CogLevelQuest, ToontownGlobals.LawbotHQ, 25, 9), Any, ToonHQ, Any, NA, DefaultDialog),
    9182: (DL_TIER + 3, Start, (StageQuest, ToontownGlobals.LawbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9183: (DL_TIER + 3, Start, (SkelecogQuest, ToontownGlobals.LawbotStageIntB, 16), Any, ToonHQ, Any, NA,
           DefaultDialog),
    9184: (DL_TIER + 3, Start, (ClerkQuest, ToontownGlobals.LawbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9185: (DL_TIER + 3, Start, (CJQuest, ToontownGlobals.LawbotHQ, 1), Any, ToonHQ, 621, NA, DefaultDialog),

    # Bossbot HQ quests
    9190: (DL_TIER + 3, Start, (CogQuest, ToontownGlobals.BossbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    9191: (DL_TIER + 3, Start, (CogLevelQuest, ToontownGlobals.BossbotHQ, 25, 11), Any, ToonHQ, Any, NA, DefaultDialog),
    9192: (DL_TIER + 3, Start, (ClubQuest, ToontownGlobals.BossbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9193: (DL_TIER + 3, Start, (SkelecogQuest, ToontownGlobals.BossbotCountryClubIntA, 8), Any, ToonHQ, Any, NA,
           DefaultDialog),
    9194: (DL_TIER + 3, Start, (PresidentQuest, ToontownGlobals.BossbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    9195: (DL_TIER + 3, Start, (CEOQuest, ToontownGlobals.BossbotHQ, 1), Any, ToonHQ, 622, NA, DefaultDialog),

    # ID 9200 - 9989 Available

    # Take on the final challenge! Defeat every boss for the Final Track Frame.
    9990: (FINALE_TIER, Start, (VisitQuest,), Any, 2001, NA, 9991, TTLocalizer.QuestDialogDict[9990]),
    9991: (FINALE_TIER, Cont, (VPQuest, ToontownGlobals.SellbotHQ, 4), Same, Same, NA, 9992,
           TTLocalizer.QuestDialogDict[9991]),
    9992: (FINALE_TIER, Cont, (CFOQuest, ToontownGlobals.CashbotHQ, 3), Same, Same, NA, 9993,
           TTLocalizer.QuestDialogDict[9992]),
    9993: (FINALE_TIER, Cont, (CJQuest, ToontownGlobals.LawbotHQ, 2), Same, Same, NA, 9994,
           TTLocalizer.QuestDialogDict[9993]),
    9994: (FINALE_TIER, Cont, (CEOQuest, ToontownGlobals.BossbotHQ, 1), Same, Same, 812, NA,
           TTLocalizer.QuestDialogDict[9994]),

    # Defeat cogs - bread and butter stuff
    10100: (ELDER_TIER, Start, (CogQuest, Anywhere, 40, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10101: (ELDER_TIER, Start, (CogQuest, Anywhere, 60, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10102: (ELDER_TIER, Start, (CogQuest, Anywhere, 80, Any), Any, ToonHQ, Any, NA, DefaultDialog),

    # Defeat lots of Cogs for lots of jellybeans
    10103: (ELDER_TIER, Start, (CogQuest, Anywhere, 100, Any), Any, ToonHQ, 615, NA, DefaultDialog),
    10104: (ELDER_TIER, Start, (CogQuest, Anywhere, 125, Any), Any, ToonHQ, 616, NA, DefaultDialog),
    10105: (ELDER_TIER, Start, (CogQuest, Anywhere, 150, Any), Any, ToonHQ, 617, NA, DefaultDialog),
    10106: (ELDER_TIER, Start, (CogQuest, Anywhere, 200, Any), Any, ToonHQ, 619, NA, DefaultDialog),

    # Defeat buildings for random rewards
    10110: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 8, Any, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    10111: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 5, Any, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    10112: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 4, Any, 4), Any, ToonHQ, Any, NA, DefaultDialog),
    10113: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 2, Any, 5), Any, ToonHQ, Any, NA, DefaultDialog),
    10114: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 1, 'm', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    10115: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 1, 's', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    10116: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 1, 'c', 5), Any, ToonHQ, Any, NA, DefaultDialog),
    10117: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 1, 'l', 5), Any, ToonHQ, Any, NA, DefaultDialog),

    # Defeat buildings for lots of beans
    10118: (ELDER_TIER, Start, (BuildingQuest, Anywhere, 10, Any, 1), Any, ToonHQ, 620, NA, DefaultDialog),

    # Sellbot HQ quests
    10120: (ELDER_TIER, Start, (CogQuest, ToontownGlobals.SellbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10121: (ELDER_TIER, Start, (FactoryQuest, ToontownGlobals.SellbotHQ, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    10122: (ELDER_TIER, Start, (ForemanQuest, ToontownGlobals.SellbotHQ, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    10123: (ELDER_TIER, Start, (VPQuest, ToontownGlobals.SellbotHQ, 3), Any, ToonHQ, 623, NA, DefaultDialog),

    # Cashbot HQ quests
    10130: (ELDER_TIER, Start, (CogQuest, ToontownGlobals.CashbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10131: (ELDER_TIER, Start, (MintQuest, ToontownGlobals.CashbotHQ, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    10132: (ELDER_TIER, Start, (SupervisorQuest, ToontownGlobals.CashbotHQ, 3), Any, ToonHQ, Any, NA, DefaultDialog),
    10133: (ELDER_TIER, Start, (CFOQuest, ToontownGlobals.CashbotHQ, 3), Any, ToonHQ, 623, NA, DefaultDialog),

    # Lawbot HQ quests
    10140: (ELDER_TIER, Start, (CogQuest, ToontownGlobals.LawbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10141: (ELDER_TIER, Start, (StageQuest, ToontownGlobals.LawbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    10142: (ELDER_TIER, Start, (ClerkQuest, ToontownGlobals.LawbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    10143: (ELDER_TIER, Start, (CJQuest, ToontownGlobals.LawbotHQ, 2), Any, ToonHQ, 623, NA, DefaultDialog),

    # Bossbot HQ quests
    10150: (ELDER_TIER, Start, (CogQuest, ToontownGlobals.BossbotHQ, 50, Any), Any, ToonHQ, Any, NA, DefaultDialog),
    10151: (ELDER_TIER, Start, (ClubQuest, ToontownGlobals.BossbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    10152: (ELDER_TIER, Start, (PresidentQuest, ToontownGlobals.BossbotHQ, 2), Any, ToonHQ, Any, NA, DefaultDialog),
    10153: (ELDER_TIER, Start, (CEOQuest, ToontownGlobals.BossbotHQ, 2), Any, ToonHQ, 623, NA, DefaultDialog),

}
# End QuestDict

Tier2QuestsDict = {}
for questId, questDesc in QuestDict.items():
    if questDesc[QuestDictStartIndex] == Start:
        tier = questDesc[QuestDictTierIndex]
        if tier in Tier2QuestsDict:
            Tier2QuestsDict[tier].append(questId)
        else:
            Tier2QuestsDict[tier] = [questId]

Quest2RewardDict = {}
Tier2Reward2QuestsDict = {}
Quest2RemainingStepsDict = {}


def getAllRewardIdsForReward(rewardId):
    if rewardId is AnyCashbotSuitPart:
        return xrange(4000, 4011 + 1)
    if rewardId is AnyLawbotSuitPart:
        return xrange(4100, 4113 + 1)
    if rewardId is AnyBossbotSuitPart:
        return xrange(4200, 4216 + 1)
    return (rewardId,)


def findFinalRewardId(questId):
    finalRewardId = Quest2RewardDict.get(questId)
    if finalRewardId:
        remainingSteps = Quest2RemainingStepsDict.get(questId)
    else:
        try:
            questDesc = QuestDict[questId]
        except KeyError:
            print 'findFinalRewardId: Quest ID: %d not found' % questId
            return -1

        nextQuestId = questDesc[QuestDictNextQuestIndex]
        if nextQuestId == NA:
            finalRewardId = questDesc[QuestDictRewardIndex]
            remainingSteps = 1
        else:
            if type(nextQuestId) == type(()):
                finalRewardId, remainingSteps = findFinalRewardId(nextQuestId[0])
                for id in nextQuestId[1:]:
                    findFinalRewardId(id)

            else:
                finalRewardId, remainingSteps = findFinalRewardId(nextQuestId)
            remainingSteps += 1
        if finalRewardId != OBSOLETE:
            if questDesc[QuestDictStartIndex] == Start:
                tier = questDesc[QuestDictTierIndex]
                tier2RewardDict = Tier2Reward2QuestsDict.setdefault(tier, {})
                rewardIds = getAllRewardIdsForReward(finalRewardId)
                for rewardId in rewardIds:
                    questList = tier2RewardDict.setdefault(rewardId, [])
                    questList.append(questId)

        else:
            finalRewardId = None
        Quest2RewardDict[questId] = finalRewardId
        Quest2RemainingStepsDict[questId] = remainingSteps
    return finalRewardId, remainingSteps


for questId in QuestDict.keys():
    findFinalRewardId(questId)


def getStartingQuests(tier=None):
    startingQuests = []
    for questId in QuestDict.keys():
        if isStartingQuest(questId):
            if tier is None:
                startingQuests.append(questId)
            elif questId in Tier2QuestsDict[tier]:
                startingQuests.append(questId)

    startingQuests.sort()
    return startingQuests


def getFinalRewardId(questId, fAll=0):
    if fAll or isStartingQuest(questId):
        return Quest2RewardDict.get(questId)
    else:
        return None
    return None


def isStartingQuest(questId):
    try:
        return QuestDict[questId][QuestDictStartIndex] == Start
    except KeyError:
        return None

    return None


def getNumChoices(tier):
    if tier in (0,):
        return 0
    if tier in (1,):
        return 2
    else:
        return 3


def getAvatarRewardId(av, questId):
    for quest in av.quests:
        if questId == quest[0]:
            return quest[3]

    notify.warning('getAvatarRewardId(): quest not found on avatar')
    return None


def getNextQuest(id, currentNpc, av):
    nextQuest = QuestDict[id][QuestDictNextQuestIndex]
    if nextQuest == NA:
        return NA, NA
    elif type(nextQuest) == type(()):
        nextReward = QuestDict[nextQuest[0]][QuestDictRewardIndex]
        nextNextQuest, nextNextToNpcId = getNextQuest(nextQuest[0], currentNpc, av)
        nextQuest = random.choice(nextQuest)
    if not getQuestClass(nextQuest).filterFunc(av):
        return getNextQuest(nextQuest, currentNpc, av)
    nextToNpcId = getQuestToNpcId(nextQuest)
    if nextToNpcId == Any:
        nextToNpcId = 2004
    elif nextToNpcId == Same:
        if currentNpc.getHq():
            nextToNpcId = ToonHQ
        else:
            nextToNpcId = currentNpc.getNpcId()
    elif nextToNpcId == ToonHQ:
        nextToNpcId = ToonHQ
    return nextQuest, nextToNpcId


def filterQuests(entireQuestPool, currentNpc, av):
    if notify.getDebug():
        notify.debug('filterQuests: entireQuestPool: %s' % entireQuestPool)
    validQuestPool = dict([(questId, 1) for questId in entireQuestPool])
    if isLoopingFinalTier(av.getRewardTier()):
        history = map(lambda questDesc: questDesc[0], av.quests)
    else:
        history = av.getQuestHistory()
    if notify.getDebug():
        notify.debug('filterQuests: av quest history: %s' % history)
    currentQuests = av.quests
    for questId in entireQuestPool:
        if questId in history:
            if notify.getDebug():
                notify.debug('filterQuests: Removed %s because in history' % questId)
            validQuestPool[questId] = 0
            continue
        potentialFromNpc = getQuestFromNpcId(questId)
        if not npcMatches(potentialFromNpc, currentNpc):
            if notify.getDebug():
                notify.debug('filterQuests: Removed %s: potentialFromNpc does not match currentNpc' % questId)
            validQuestPool[questId] = 0
            continue
        potentialToNpc = getQuestToNpcId(questId)
        if currentNpc.getNpcId() == potentialToNpc:
            if notify.getDebug():
                notify.debug('filterQuests: Removed %s because potentialToNpc is currentNpc' % questId)
            validQuestPool[questId] = 0
            continue
        if not getQuestClass(questId).filterFunc(av):
            if notify.getDebug():
                notify.debug('filterQuests: Removed %s because of filterFunc' % questId)
            validQuestPool[questId] = 0
            continue
        for quest in currentQuests:
            fromNpcId = quest[1]
            toNpcId = quest[2]
            if potentialToNpc == toNpcId and toNpcId != ToonHQ:
                validQuestPool[questId] = 0
                if notify.getDebug():
                    notify.debug('filterQuests: Removed %s because npc involved' % questId)
                break

    finalQuestPool = filter(lambda key: validQuestPool[key], validQuestPool.keys())
    if notify.getDebug():
        notify.debug('filterQuests: finalQuestPool: %s' % finalQuestPool)
    return finalQuestPool


def chooseTrackChoiceQuest(tier, av, fixed=0):
    trackAccess = av.getTrackAccess()
    if tier == DD_TIER:
        bestQuest = 1400
    elif tier == MM_TIER:
        bestQuest = 4001
    elif tier == BR_TIER:
        bestQuest = 5001
    else:
        if notify.getDebug():
            notify.debug('questPool for reward 400 had no dynamic choice, tier: %s' % tier)
        bestQuest = seededRandomChoice(Tier2Reward2QuestsDict[tier][400])
    if notify.getDebug():
        notify.debug('chooseTrackChoiceQuest: avId: %s trackAccess: %s tier: %s bestQuest: %s' % (av.getDoId(),
                                                                                                  trackAccess,
                                                                                                  tier,
                                                                                                  bestQuest))
    return bestQuest


def chooseMatchingQuest(tier, validQuestPool, rewardId, npc, av):
    questsMatchingReward = Tier2Reward2QuestsDict[tier].get(rewardId, [])
    if notify.getDebug():
        notify.debug('questsMatchingReward: %s tier: %s = %s' % (rewardId, tier, questsMatchingReward))
    validQuestsMatchingReward = PythonUtil.intersection(questsMatchingReward, validQuestPool)
    if notify.getDebug():
        notify.debug('validQuestsMatchingReward: %s tier: %s = %s' % (rewardId, tier, validQuestsMatchingReward))
    if validQuestsMatchingReward:
        bestQuest = seededRandomChoice(validQuestsMatchingReward)
    else:
        questsMatchingReward = Tier2Reward2QuestsDict[tier].get(AnyCashbotSuitPart, [])
        if notify.getDebug():
            notify.debug('questsMatchingReward: AnyCashbotSuitPart tier: %s = %s' % (tier, questsMatchingReward))
        validQuestsMatchingReward = PythonUtil.intersection(questsMatchingReward, validQuestPool)
        if validQuestsMatchingReward:
            if notify.getDebug():
                notify.debug('validQuestsMatchingReward: AnyCashbotSuitPart tier: %s = %s' % (
                    tier, validQuestsMatchingReward))
            bestQuest = seededRandomChoice(validQuestsMatchingReward)
        else:
            questsMatchingReward = Tier2Reward2QuestsDict[tier].get(AnyLawbotSuitPart, [])
            if notify.getDebug():
                notify.debug('questsMatchingReward: AnyLawbotSuitPart tier: %s = %s' % (tier, questsMatchingReward))
            validQuestsMatchingReward = PythonUtil.intersection(questsMatchingReward, validQuestPool)
            if validQuestsMatchingReward:
                if notify.getDebug():
                    notify.debug('validQuestsMatchingReward: AnyLawbotSuitPart tier: %s = %s' % (
                        tier, validQuestsMatchingReward))
                bestQuest = seededRandomChoice(validQuestsMatchingReward)
            else:
                questsMatchingReward = Tier2Reward2QuestsDict[tier].get(Any, [])
                if notify.getDebug():
                    notify.debug('questsMatchingReward: Any tier: %s = %s' % (tier, questsMatchingReward))
                if not questsMatchingReward:
                    notify.warning('chooseMatchingQuests, no questsMatchingReward')
                    return None
                validQuestsMatchingReward = PythonUtil.intersection(questsMatchingReward, validQuestPool)
                if not validQuestsMatchingReward:
                    notify.warning('chooseMatchingQuests, no validQuestsMatchingReward')
                    return None
                if notify.getDebug():
                    notify.debug('validQuestsMatchingReward: Any tier: %s = %s' % (tier, validQuestsMatchingReward))
                bestQuest = seededRandomChoice(validQuestsMatchingReward)
    return bestQuest


def chooseBestQuests(tier, currentNpc, av):
    if isLoopingFinalTier(tier):
        rewardHistory = map(lambda questDesc: questDesc[3], av.quests)
    else:
        rewardHistory = av.getRewardHistory()[1]
    seedRandomGen(currentNpc.getNpcId(), av.getDoId(), tier, rewardHistory)
    numChoices = getNumChoices(tier)
    rewards = getNextRewards(numChoices, tier, av)
    if not rewards:
        return []
    possibleQuests = []
    possibleRewards = list(rewards)
    if Any not in possibleRewards:
        possibleRewards.append(Any)
    for rewardId in possibleRewards:
        possibleQuests.extend(Tier2Reward2QuestsDict[tier].get(rewardId, []))

    validQuestPool = filterQuests(possibleQuests, currentNpc, av)
    if not validQuestPool:
        return []
    if numChoices == 0:
        numChoices = 1
    bestQuests = []
    for i in xrange(numChoices):
        if len(validQuestPool) == 0:
            break
        if len(rewards) == 0:
            break
        rewardId = rewards.pop(0)
        bestQuestId = chooseMatchingQuest(tier, validQuestPool, rewardId, currentNpc, av)
        if bestQuestId is None:
            continue
        validQuestPool.remove(bestQuestId)
        bestQuestToNpcId = getQuestToNpcId(bestQuestId)
        if bestQuestToNpcId == Any:
            bestQuestToNpcId = 2003
        elif bestQuestToNpcId == Same:
            if currentNpc.getHq():
                bestQuestToNpcId = ToonHQ
            else:
                bestQuestToNpcId = currentNpc.getNpcId()
        elif bestQuestToNpcId == ToonHQ:
            bestQuestToNpcId = ToonHQ
        bestQuests.append([bestQuestId, rewardId, bestQuestToNpcId])

    for quest in bestQuests:
        reward_id = quest[1]
        quest[1] = reward_id

    return bestQuests


def questExists(id):
    return id in QuestDict


def getQuest(id):
    questEntry = QuestDict.get(id)
    if questEntry:
        questDesc = questEntry[QuestDictDescIndex]
        questClass = questDesc[0]
        return questClass(id, questDesc[1:])
    else:
        return None
    return None


def getQuestClass(id):
    questEntry = QuestDict.get(id)
    if questEntry:
        return questEntry[QuestDictDescIndex][0]
    else:
        return None
    return None


def getVisitSCStrings(npcId):
    if npcId == ToonHQ:
        strings = [TTLocalizer.QuestsRecoverItemQuestSeeHQSCString, TTLocalizer.QuestsRecoverItemQuestGoToHQSCString]
    elif npcId == ToonTailor:
        strings = [TTLocalizer.QuestsTailorQuestSCString]
    elif npcId:
        npcName, hoodName, buildingArticle, buildingName, toStreet, streetName, isInPlayground = getNpcInfo(npcId)
        strings = [TTLocalizer.QuestsVisitQuestSeeSCString % npcName]
        if isInPlayground:
            strings.append(TTLocalizer.QuestsRecoverItemQuestGoToPlaygroundSCString % hoodName)
        else:
            strings.append(TTLocalizer.QuestsRecoverItemQuestGoToStreetSCString % {'to': toStreet,
                                                                                   'street': streetName,
                                                                                   'hood': hoodName})
        strings.extend([TTLocalizer.QuestsRecoverItemQuestVisitBuildingSCString % (buildingArticle, buildingName),
                        TTLocalizer.QuestsRecoverItemQuestWhereIsBuildingSCString % (buildingArticle, buildingName)])
    return strings


def getFinishToonTaskSCStrings(npcId):
    return [TTLocalizer.QuestsGenericFinishSCString] + getVisitSCStrings(npcId)


def chooseQuestDialog(id, status):
    questDialog = getQuestDialog(id).get(status)
    if questDialog is None:
        if status == QUEST:
            quest = getQuest(id)
            questDialog = quest.getDefaultQuestDialog()
        else:
            questDialog = DefaultDialog[status]
    if type(questDialog) == type(()):
        return random.choice(questDialog)
    else:
        return questDialog
    return


def chooseQuestDialogReject():
    return random.choice(DefaultReject)


def chooseQuestDialogTierNotDone():
    return random.choice(DefaultTierNotDone)


def getNpcInfo(npcId):
    npcName = NPCToons.getNPCName(npcId)
    npcZone = NPCToons.getNPCZone(npcId)
    hoodId = ZoneUtil.getCanonicalHoodId(npcZone)
    hoodName = base.cr.hoodMgr.getFullnameFromId(hoodId)
    buildingArticle = NPCToons.getBuildingArticle(npcZone)
    buildingName = NPCToons.getBuildingTitle(npcZone)
    branchId = ZoneUtil.getCanonicalBranchZone(npcZone)
    toStreet = ToontownGlobals.StreetNames[branchId][0]
    streetName = ToontownGlobals.StreetNames[branchId][-1]
    isInPlayground = ZoneUtil.isPlayground(branchId)
    return (npcName,
            hoodName,
            buildingArticle,
            buildingName,
            toStreet,
            streetName,
            isInPlayground)


def getNpcLocationDialog(fromNpcId, toNpcId):
    if not toNpcId:
        return None, None, None
    fromNpcZone = None
    fromBranchId = None
    if fromNpcId:
        fromNpcZone = NPCToons.getNPCZone(fromNpcId)
        fromBranchId = ZoneUtil.getCanonicalBranchZone(fromNpcZone)
    toNpcZone = NPCToons.getNPCZone(toNpcId)
    toBranchId = ZoneUtil.getCanonicalBranchZone(toNpcZone)
    toNpcName, toHoodName, toBuildingArticle, toBuildingName, toStreetTo, toStreetName, isInPlayground = getNpcInfo(
        toNpcId)
    if fromBranchId == toBranchId:
        if isInPlayground:
            streetDesc = TTLocalizer.QuestsStreetLocationThisPlayground
        else:
            streetDesc = TTLocalizer.QuestsStreetLocationThisStreet
    elif isInPlayground:
        streetDesc = TTLocalizer.QuestsStreetLocationNamedPlayground % toHoodName
    else:
        streetDesc = TTLocalizer.QuestsStreetLocationNamedStreet % {'toStreetName': toStreetName,
                                                                    'toHoodName': toHoodName}
    paragraph = TTLocalizer.QuestsLocationParagraph % {'building': TTLocalizer.QuestsLocationBuilding % toNpcName,
                                                       'buildingName': toBuildingName,
                                                       'buildingVerb': TTLocalizer.QuestsLocationBuildingVerb,
                                                       'street': streetDesc}
    return paragraph, toBuildingName, streetDesc


def fillInQuestNames(text, avName=None, fromNpcId=None, toNpcId=None):
    text = copy.deepcopy(text)
    if avName:
        text = string.replace(text, '_avName_', avName)
    if toNpcId:
        if toNpcId == ToonHQ:
            toNpcName = TTLocalizer.QuestsHQOfficerFillin
            where = TTLocalizer.QuestsHQWhereFillin
            buildingName = TTLocalizer.QuestsHQBuildingNameFillin
            streetDesc = TTLocalizer.QuestsHQLocationNameFillin
        elif toNpcId == ToonTailor:
            toNpcName = TTLocalizer.QuestsTailorFillin
            where = TTLocalizer.QuestsTailorWhereFillin
            buildingName = TTLocalizer.QuestsTailorBuildingNameFillin
            streetDesc = TTLocalizer.QuestsTailorLocationNameFillin
        else:
            toNpcName = str(NPCToons.getNPCName(toNpcId))
            where, buildingName, streetDesc = getNpcLocationDialog(fromNpcId, toNpcId)
        text = string.replace(text, '_toNpcName_', toNpcName)
        text = string.replace(text, '_where_', where)
        text = string.replace(text, '_buildingName_', buildingName)
        text = string.replace(text, '_streetDesc_', streetDesc)
    return text


def getVisitingQuest():
    return VisitQuest(VISIT_QUEST_ID)


class Reward:
    def __init__(self, id, reward):
        self.id = id
        self.reward = reward

    def getId(self):
        return self.id

    def getType(self):
        return self.__class__

    def getAmount(self):
        return None

    def sendRewardAI(self, av):
        raise 'not implemented'

    def countReward(self, qrc):
        raise 'not implemented'

    def getString(self):
        return 'undefined'

    def getPosterString(self):
        return 'base class'


class MaxHpReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getAmount(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        maxHp = av.getMaxHp()
        maxHp = min(ToontownGlobals.MaxHpLimit, maxHp + self.getAmount())
        av.b_setMaxHp(maxHp)
        av.toonUp(maxHp)

    def countReward(self, qrc):
        qrc.maxHp += self.getAmount()

    def getString(self):
        return TTLocalizer.QuestsMaxHpReward % self.getAmount()

    def getPosterString(self):
        return TTLocalizer.QuestsMaxHpRewardPoster % self.getAmount()


class MoneyReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getAmount(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        money = av.getMoney()
        maxMoney = av.getMaxMoney()
        av.addMoney(self.getAmount())

    def countReward(self, qrc):
        qrc.money += self.getAmount()

    def getString(self):
        amt = self.getAmount()
        if amt == 1:
            return TTLocalizer.QuestsMoneyRewardSingular
        else:
            return TTLocalizer.QuestsMoneyRewardPlural % amt

    def getPosterString(self):
        amt = self.getAmount()
        if amt == 1:
            return TTLocalizer.QuestsMoneyRewardPosterSingular
        else:
            return TTLocalizer.QuestsMoneyRewardPosterPlural % amt


class MaxMoneyReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getAmount(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        av.b_setMaxMoney(self.getAmount())

    def countReward(self, qrc):
        qrc.maxMoney = self.getAmount()

    def getString(self):
        amt = self.getAmount()
        if amt == 1:
            return TTLocalizer.QuestsMaxMoneyRewardSingular
        else:
            return TTLocalizer.QuestsMaxMoneyRewardPlural % amt

    def getPosterString(self):
        amt = self.getAmount()
        if amt == 1:
            return TTLocalizer.QuestsMaxMoneyRewardPosterSingular
        else:
            return TTLocalizer.QuestsMaxMoneyRewardPosterPlural % amt


class MaxGagCarryReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getAmount(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        av.b_setMaxCarry(self.getAmount())

    def countReward(self, qrc):
        qrc.maxCarry = self.getAmount()

    def getString(self):
        amt = self.getAmount()
        return TTLocalizer.QuestsMaxGagCarryReward % {'num': amt}

    def getPosterString(self):
        amt = self.getAmount()
        return TTLocalizer.QuestsMaxGagCarryRewardPoster % {'num': amt}


class MaxQuestCarryReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getAmount(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        av.b_setQuestCarryLimit(self.getAmount())

    def countReward(self, qrc):
        qrc.questCarryLimit = self.getAmount()

    def getString(self):
        amt = self.getAmount()
        return TTLocalizer.QuestsMaxQuestCarryReward % amt

    def getPosterString(self):
        amt = self.getAmount()
        return TTLocalizer.QuestsMaxQuestCarryRewardPoster % amt


class TeleportReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getZone(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        av.addTeleportAccess(self.getZone())

    def countReward(self, qrc):
        qrc.addTeleportAccess(self.getZone())

    def getString(self):
        hoodName = ToontownGlobals.hoodNameMap[self.getZone()][-1]
        return TTLocalizer.QuestsTeleportReward % hoodName

    def getPosterString(self):
        hoodName = ToontownGlobals.hoodNameMap[self.getZone()][-1]
        return TTLocalizer.QuestsTeleportRewardPoster % hoodName


class TrainingFrameReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getFrameIndex(self):
        return self.reward[0]

    def sendRewardAI(self, av):
        av.addTrainingFrame(self.getFrameIndex())

    def countReward(self, qrc):
        qrc.addTrainingFrame(self.getFrameIndex())

    def getString(self):
        return TTLocalizer.QuestsTrainingFrameReward % (self.getFrameIndex() + 1)

    def getPosterString(self):
        return TTLocalizer.QuestsTrainingFrameRewardPoster % (self.getFrameIndex() + 1)


class FrameRefundAward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getPoints(self):
        amount = self.reward[0]
        if amount is None:
            amount = 0
        return amount

    def sendRewardAI(self, av):
        av.b_setRefundPoints(av.getRefundPoints() + self.getPoints())

    def countReward(self, qrc):
        qrc.setRefundPoints(qrc.getRefundPoints() + self.getPoints())

    def getString(self):
        return TTLocalizer.QuestsFrameRefundReward

    def getPosterString(self):
        return TTLocalizer.QuestsFrameRefundRewardPoster


class TrainingCompleteReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def sendRewardAI(self, av):
        av.addTrainingFrame(MaxTrainingFrames - 1)

    def countReward(self, qrc):
        qrc.addTrainingFrame(MaxTrainingFrames - 1)

    def getString(self):
        return TTLocalizer.QuestsTrainingCompleteReward

    def getPosterString(self):
        return TTLocalizer.QuestsTrainingCompleteRewardPoster


class ClothingTicketReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def sendRewardAI(self, av):
        pass

    def countReward(self, qrc):
        pass

    def getString(self):
        return TTLocalizer.QuestsClothingTicketReward

    def getPosterString(self):
        return TTLocalizer.QuestsClothingTicketRewardPoster


class TIPClothingTicketReward(ClothingTicketReward):
    def __init__(self, id, reward):
        ClothingTicketReward.__init__(self, id, reward)

    def getString(self):
        return TTLocalizer.TIPQuestsClothingTicketReward

    def getPosterString(self):
        return TTLocalizer.TIPQuestsClothingTicketRewardPoster


class CheesyEffectReward(Reward):
    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getEffect(self):
        return self.reward[0]

    def getHoodId(self):
        return self.reward[1]

    def getDurationMinutes(self):
        return self.reward[2]

    def sendRewardAI(self, av):
        expireTime = int(time.time() / 60 + 0.5) + self.getDurationMinutes()
        av.b_setCheesyEffect(self.getEffect(), self.getHoodId(), expireTime)

    def countReward(self, qrc):
        pass

    def getString(self):
        effect = self.getEffect()
        hoodId = self.getHoodId()
        duration = self.getDurationMinutes()
        string = TTLocalizer.CheesyEffectMinutes
        if duration > 90:
            duration = int((duration + 30) / 60)
            string = TTLocalizer.CheesyEffectHours
            if duration > 36:
                duration = int((duration + 12) / 24)
                string = TTLocalizer.CheesyEffectDays
        desc = TTLocalizer.CheesyEffectDescriptions[effect][1]
        if hoodId == 0:
            whileStr = ''
        elif hoodId == 1:
            whileStr = TTLocalizer.CheesyEffectExceptIn % TTLocalizer.ToontownCentral[-1]
        else:
            hoodName = base.cr.hoodMgr.getFullnameFromId(hoodId)
            whileStr = TTLocalizer.CheesyEffectWhileYouAreIn % hoodName
        if duration:
            return string % {'time': duration,
                             'effectName': desc,
                             'whileIn': whileStr}
        else:
            return TTLocalizer.CheesyEffectIndefinite % {'effectName': desc,
                                                         'whileIn': whileStr}

    def getPosterString(self):
        effect = self.getEffect()
        desc = TTLocalizer.CheesyEffectDescriptions[effect][0]
        return TTLocalizer.QuestsCheesyEffectRewardPoster % desc


class CogSuitPartReward(Reward):
    trackNames = [TTLocalizer.Bossbot,
                  TTLocalizer.Lawbot,
                  TTLocalizer.Cashbot,
                  TTLocalizer.Sellbot]

    def __init__(self, id, reward):
        Reward.__init__(self, id, reward)

    def getCogTrack(self):
        return self.reward[0]

    def getCogPart(self):
        return self.reward[1]

    def sendRewardAI(self, av):
        dept = self.getCogTrack()
        part = self.getCogPart()
        av.giveCogPart(part, dept)

    def countReward(self, qrc):
        pass

    def getCogTrackName(self):
        index = ToontownGlobals.cogDept2index[self.getCogTrack()]
        return CogSuitPartReward.trackNames[index]

    def getCogPartName(self):
        index = ToontownGlobals.cogDept2index[self.getCogTrack()]
        return CogDisguiseGlobals.PartsQueryNames[index][self.getCogPart()]

    def getString(self):
        return TTLocalizer.QuestsCogSuitPartReward % {'cogTrack': self.getCogTrackName(),
                                                      'part': self.getCogPartName()}

    def getPosterString(self):
        return TTLocalizer.QuestsCogSuitPartRewardPoster % {'cogTrack': self.getCogTrackName(),
                                                            'part': self.getCogPartName()}


def getRewardClass(id):
    reward = RewardDict.get(id)
    if reward:
        return reward[0]
    else:
        return None
    return None


def getReward(id):
    reward = RewardDict.get(id)
    if reward:
        rewardClass = reward[0]
        return rewardClass(id, reward[1:])
    else:
        notify.warning('getReward(): id %s not found.' % id)
        return None
    return None


def getNextRewards(numChoices, tier, av):
    rewardTier = list(getRewardsInTier(tier))
    optRewards = list(getOptionalRewardsInTier(tier))
    if av.getGameAccess() == OTPGlobals.AccessFull and tier == TT_TIER + 3:
        optRewards = []
    if isLoopingFinalTier(tier):
        rewardHistory = map(lambda questDesc: questDesc[3], av.quests)
        if notify.getDebug():
            notify.debug('getNextRewards: current rewards (history): %s' % rewardHistory)
    else:
        rewardHistory = av.getRewardHistory()[1]
        if notify.getDebug():
            notify.debug('getNextRewards: rewardHistory: %s' % rewardHistory)
    if notify.getDebug():
        notify.debug('getNextRewards: rewardTier: %s' % rewardTier)
        notify.debug('getNextRewards: numChoices: %s' % numChoices)
    potentialRewards = getRewardsInTier(tier)
    for rewardId in potentialRewards:
        if getRewardClass(rewardId) == CogSuitPartReward:
            deptStr = RewardDict.get(rewardId)[1]
            cogPart = RewardDict.get(rewardId)[2]
            dept = ToontownGlobals.cogDept2index[deptStr]
            if av.hasCogPart(cogPart, dept):
                notify.debug('getNextRewards: already has cog part: %s dept: %s' % (cogPart, dept))
                rewardTier.remove(rewardId)
            else:
                notify.debug('getNextRewards: keeping quest for cog part: %s dept: %s' % (cogPart, dept))

    for rewardId in rewardHistory:
        if rewardId in rewardTier:
            rewardTier.remove(rewardId)
        elif rewardId in optRewards:
            optRewards.remove(rewardId)

    if numChoices == 0:
        if len(rewardTier) == 0:
            return []
        else:
            return [rewardTier[0]]
    rewardPool = rewardTier[:numChoices]
    for i in xrange(len(rewardPool), numChoices * 2):
        if optRewards:
            optionalReward = seededRandomChoice(optRewards)
            optRewards.remove(optionalReward)
            rewardPool.append(optionalReward)
        else:
            break

    if notify.getDebug():
        notify.debug('getNextRewards: starting reward pool: %s' % rewardPool)
    if len(rewardPool) == 0:
        if notify.getDebug():
            notify.debug('getNextRewards: no rewards left at all')
        return []
    finalRewardPool = [rewardPool.pop(0)]
    for i in xrange(numChoices - 1):
        if len(rewardPool) == 0:
            break
        selectedReward = seededRandomChoice(rewardPool)
        rewardPool.remove(selectedReward)
        finalRewardPool.append(selectedReward)

    if notify.getDebug():
        notify.debug('getNextRewards: final reward pool: %s' % finalRewardPool)
    return finalRewardPool


RewardDict = {100: (MaxHpReward, 1),
              101: (MaxHpReward, 2),
              102: (MaxHpReward, 3),
              103: (MaxHpReward, 4),
              104: (MaxHpReward, 5),
              105: (MaxHpReward, 6),
              106: (MaxHpReward, 7),
              107: (MaxHpReward, 8),
              108: (MaxHpReward, 9),
              109: (MaxHpReward, 10),
              110: (TIPClothingTicketReward,),
              200: (MaxGagCarryReward, 25),
              201: (MaxGagCarryReward, 30),
              202: (MaxGagCarryReward, 35),
              203: (MaxGagCarryReward, 40),
              204: (MaxGagCarryReward, 45),
              205: (MaxGagCarryReward, 50),
              206: (MaxGagCarryReward, 55),
              207: (MaxGagCarryReward, 60),
              208: (MaxGagCarryReward, 65),
              209: (MaxGagCarryReward, 70),
              210: (MaxGagCarryReward, 75),
              211: (MaxGagCarryReward, 80),
              212: (MaxGagCarryReward, 85),
              213: (MaxGagCarryReward, 90),
              214: (MaxGagCarryReward, 100),
              300: (TeleportReward, ToontownGlobals.ToontownCentral),
              301: (TeleportReward, ToontownGlobals.DonaldsDock),
              302: (TeleportReward, ToontownGlobals.DaisyGardens),
              303: (TeleportReward, ToontownGlobals.MinniesMelodyland),
              304: (TeleportReward, ToontownGlobals.TheBrrrgh),
              305: (TeleportReward, ToontownGlobals.DonaldsDreamland),
              400: (FrameRefundAward, 1),
              401: (FrameRefundAward, 1),
              402: (FrameRefundAward, 1),
              500: (MaxQuestCarryReward, 2),
              501: (MaxQuestCarryReward, 3),
              502: (MaxQuestCarryReward, 4),
              600: (MoneyReward, 20),
              601: (MoneyReward, 40),
              602: (MoneyReward, 60),
              603: (MoneyReward, 80),
              604: (MoneyReward, 150),
              605: (MoneyReward, 200),
              606: (MoneyReward, 300),
              607: (MoneyReward, 400),
              608: (MoneyReward, 500),
              609: (MoneyReward, 600),
              610: (MoneyReward, 700),
              611: (MoneyReward, 800),
              612: (MoneyReward, 900),
              613: (MoneyReward, 1000),
              614: (MoneyReward, 1100),
              615: (MoneyReward, 1200),
              616: (MoneyReward, 1300),
              617: (MoneyReward, 1400),
              618: (MoneyReward, 1500),
              619: (MoneyReward, 1600),
              620: (MoneyReward, 1750),
              621: (MoneyReward, 2000),
              622: (MoneyReward, 2500),
              623: (MoneyReward, 3000),
              624: (MoneyReward, 3500),
              625: (MoneyReward, 4000),
              700: (MaxMoneyReward, 50),
              701: (MaxMoneyReward, 60),
              702: (MaxMoneyReward, 80),
              703: (MaxMoneyReward, 100),
              704: (MaxMoneyReward, 120),
              705: (MaxMoneyReward, 150),
              706: (MaxMoneyReward, 200),
              707: (MaxMoneyReward, 250),
              801: (TrainingFrameReward, 4),
              802: (TrainingFrameReward, 5),
              803: (TrainingFrameReward, 6),
              804: (TrainingFrameReward, 7),
              805: (TrainingFrameReward, 8),
              806: (TrainingFrameReward, 9),
              807: (TrainingFrameReward, 10),
              808: (TrainingFrameReward, 11),
              809: (TrainingFrameReward, 12),
              810: (TrainingFrameReward, 13),
              811: (TrainingFrameReward, 14),
              812: (TrainingCompleteReward,),

              # TT
              2205: (CheesyEffectReward, ToontownGlobals.CEBigToon, 2000, 10),
              2206: (CheesyEffectReward, ToontownGlobals.CESmallToon, 2000, 10),

              # DD
              2101: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1000, 10),
              2102: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1000, 10),
              2105: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 20),
              2106: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 20),

              # DG
              2501: (CheesyEffectReward, ToontownGlobals.CEBigHead, 5000, 60),
              2502: (CheesyEffectReward, ToontownGlobals.CESmallHead, 5000, 60),
              2503: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 5000, 20),
              2504: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 5000, 20),
              2505: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 60),
              2506: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 60),

              # MM
              2401: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 120),
              2402: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 120),
              2403: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 4000, 60),
              2404: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 4000, 60),
              2405: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 120),
              2406: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 120),
              2407: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 4000, 30),
              2408: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 4000, 30),
              2409: (CheesyEffectReward, ToontownGlobals.CETransparent, 4000, 30),
              2410: (CheesyEffectReward, ToontownGlobals.CENoColor, 4000, 30),

              # BR
              2301: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 360),
              2302: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 360),
              2303: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 1, 360),
              2304: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 1, 360),
              2305: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 1440),
              2306: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 1440),
              2307: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 3000, 240),
              2308: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 3000, 240),
              2309: (CheesyEffectReward, ToontownGlobals.CETransparent, 1, 120),
              2310: (CheesyEffectReward, ToontownGlobals.CENoColor, 1, 120),
              2311: (CheesyEffectReward, ToontownGlobals.CEInvisible, 3000, 120),

              # DL, 24 hrs
              2900: (CheesyEffectReward, ToontownGlobals.CENormal, 0, 0),
              2901: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 1440),
              2902: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 1440),
              2903: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 1, 1440),
              2904: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 1, 1440),
              2905: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 1440),
              2906: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 1440),
              2907: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 1, 1440),
              2908: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 1, 1440),
              2909: (CheesyEffectReward, ToontownGlobals.CETransparent, 1, 1440),
              2910: (CheesyEffectReward, ToontownGlobals.CENoColor, 1, 1440),
              2911: (CheesyEffectReward, ToontownGlobals.CEInvisible, 1, 1440),

              # DL+1, 2 days
              2920: (CheesyEffectReward, ToontownGlobals.CENormal, 0, 0),
              2921: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 2880),
              2922: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 2880),
              2923: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 1, 2880),
              2924: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 1, 2880),
              2925: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 2880),
              2926: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 2880),
              2927: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 1, 2880),
              2928: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 1, 2880),
              2929: (CheesyEffectReward, ToontownGlobals.CETransparent, 1, 2880),
              2930: (CheesyEffectReward, ToontownGlobals.CENoColor, 1, 2880),
              2931: (CheesyEffectReward, ToontownGlobals.CEInvisible, 1, 2880),

              # DL+2, 7 days
              2940: (CheesyEffectReward, ToontownGlobals.CENormal, 0, 0),
              2941: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 10080),
              2942: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 10080),
              2943: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 1, 10080),
              2944: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 1, 10080),
              2945: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 10080),
              2946: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 10080),
              2947: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 1, 10080),
              2948: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 1, 10080),
              2949: (CheesyEffectReward, ToontownGlobals.CETransparent, 1, 10080),
              2950: (CheesyEffectReward, ToontownGlobals.CENoColor, 1, 10080),
              2951: (CheesyEffectReward, ToontownGlobals.CEInvisible, 1, 10080),

              # DL+3, 30 days
              2960: (CheesyEffectReward, ToontownGlobals.CENormal, 0, 0),
              2961: (CheesyEffectReward, ToontownGlobals.CEBigHead, 1, 43200),
              2962: (CheesyEffectReward, ToontownGlobals.CESmallHead, 1, 43200),
              2963: (CheesyEffectReward, ToontownGlobals.CEBigLegs, 1, 43200),
              2964: (CheesyEffectReward, ToontownGlobals.CESmallLegs, 1, 43200),
              2965: (CheesyEffectReward, ToontownGlobals.CEBigToon, 0, 43200),
              2966: (CheesyEffectReward, ToontownGlobals.CESmallToon, 0, 43200),
              2967: (CheesyEffectReward, ToontownGlobals.CEFlatPortrait, 1, 43200),
              2968: (CheesyEffectReward, ToontownGlobals.CEFlatProfile, 1, 43200),
              2969: (CheesyEffectReward, ToontownGlobals.CETransparent, 1, 43200),
              2970: (CheesyEffectReward, ToontownGlobals.CENoColor, 1, 43200),
              2971: (CheesyEffectReward, ToontownGlobals.CEInvisible, 1, 43200), }


def getNumTiers():
    return len(RequiredRewardTrackDict) - 1


def isLoopingFinalTier(tier):
    return tier == LOOPING_FINAL_TIER


def getRewardsInTier(tier):
    return RequiredRewardTrackDict.get(tier, [])


def getNumRewardsInTier(tier):
    return len(RequiredRewardTrackDict.get(tier, []))


def rewardTierExists(tier):
    return tier in RequiredRewardTrackDict


def getOptionalRewardsInTier(tier):
    return OptionalRewardTrackDict.get(tier, [])


RequiredRewardTrackDict = {TT_TIER: (100,),
                           TT_TIER + 1: (801,),
                           TT_TIER + 2: (100,
                                         500,
                                         101,
                                         200),
                           TT_TIER + 3: (101,
                                         300,
                                         102,
                                         201,
                                         802),
                           DD_TIER: (400,),
                           DD_TIER + 1: (101,
                                         100,
                                         202,
                                         100,
                                         803),
                           DD_TIER + 2: (100,
                                         301,
                                         102,
                                         203,
                                         101,
                                         804),
                           DG_TIER: (100,
                                     100,
                                     100,
                                     101,
                                     101,
                                     102,
                                     204,
                                     302,
                                     501,
                                     805),
                           DG_TIER + 1: (205,
                                         806,),
                           MM_TIER: (401,),
                           MM_TIER + 1: (100,
                                         100,
                                         100,
                                         101,
                                         101,
                                         102,
                                         206,
                                         303,
                                         807),
                           MM_TIER + 2: (207,
                                         808,),
                           BR_TIER: (402,),
                           BR_TIER + 1: (100,
                                         100,
                                         100,
                                         101,
                                         101,
                                         102,
                                         208,
                                         304,
                                         502,
                                         809),
                           BR_TIER + 2: (209,
                                         810,),
                           DL_TIER: (100,
                                     101,
                                     210,
                                     103,
                                     305),
                           DL_TIER + 1: (100,
                                         211,
                                         102),
                           DL_TIER + 2: (100,
                                         101,
                                         212,
                                         102,
                                         811),
                           DL_TIER + 3: (100,
                                         101,
                                         102,
                                         213,
                                         101),
                           FINALE_TIER: (812,
                                         214),
                           ELDER_TIER: ()}
OptionalRewardTrackDict = {TT_TIER: (),
                           TT_TIER + 1: (),
                           TT_TIER + 2: (601,
                                         601,
                                         602,
                                         602,
                                         2205,
                                         2206,
                                         2205,
                                         2206),
                           TT_TIER + 3: (601,
                                         601,
                                         602,
                                         602,
                                         2205,
                                         2206,
                                         2205,
                                         2206),
                           DD_TIER: (603,
                                     603,
                                     604,
                                     604,
                                     2101,
                                     2102,
                                     2105,
                                     2106),
                           DD_TIER + 1: (603,
                                         603,
                                         604,
                                         604,
                                         2101,
                                         2102,
                                         2105,
                                         2106),
                           DD_TIER + 2: (603,
                                         603,
                                         604,
                                         604,
                                         2101,
                                         2102,
                                         2105,
                                         2106),
                           DG_TIER: (605,
                                     605,
                                     606,
                                     606,
                                     2501,
                                     2502,
                                     2503,
                                     2504,
                                     2505,
                                     2506),
                           MM_TIER: (607,
                                     607,
                                     608,
                                     608,
                                     2403,
                                     2404,
                                     2405,
                                     2406,
                                     2407,
                                     2408,
                                     2409),
                           MM_TIER + 1: (607,
                                         607,
                                         608,
                                         608,
                                         2403,
                                         2404,
                                         2405,
                                         2406,
                                         2407,
                                         2408,
                                         2409),
                           MM_TIER + 2: (607,
                                         607,
                                         608,
                                         608,
                                         2403,
                                         2404,
                                         2405,
                                         2406,
                                         2407,
                                         2408,
                                         2409),
                           BR_TIER: (609,
                                     609,
                                     609,
                                     609,
                                     609,
                                     610,
                                     610,
                                     610,
                                     610,
                                     610,
                                     2305,
                                     2306,
                                     2307,
                                     2308,
                                     2309,
                                     2310,
                                     2311),
                           BR_TIER + 1: (609,
                                         609,
                                         609,
                                         609,
                                         609,
                                         610,
                                         610,
                                         610,
                                         610,
                                         610,
                                         2305,
                                         2306,
                                         2307,
                                         2308,
                                         2309,
                                         2310,
                                         2311),
                           BR_TIER + 2: (609,
                                         609,
                                         609,
                                         609,
                                         609,
                                         610,
                                         610,
                                         610,
                                         610,
                                         610,
                                         2305,
                                         2306,
                                         2307,
                                         2308,
                                         2309,
                                         2310,
                                         2311),
                           DL_TIER: (611,
                                     611,
                                     611,
                                     611,
                                     612,
                                     612,
                                     612,
                                     612,
                                     2901,
                                     2902,
                                     2907,
                                     2908,
                                     2909,
                                     2910,
                                     2911),
                           DL_TIER + 1: (611,
                                         611,
                                         611,
                                         611,
                                         612,
                                         612,
                                         612,
                                         612,
                                         2923,
                                         2924,
                                         2927,
                                         2928,
                                         2929,
                                         2930,
                                         2931),
                           DL_TIER + 2: (611,
                                         611,
                                         611,
                                         611,
                                         612,
                                         612,
                                         612,
                                         612,
                                         2941,
                                         2942,
                                         2943,
                                         2944,
                                         2947,
                                         2948,
                                         2949,
                                         2950,
                                         2951),
                           DL_TIER + 3: (613,
                                         613,
                                         613,
                                         613,
                                         613,
                                         613,
                                         2961,
                                         2962,
                                         2963,
                                         2964,
                                         2965,
                                         2966,
                                         2967,
                                         2968,
                                         2969,
                                         2970,
                                         2971),
                           ELDER_TIER: (613,
                                        614,
                                        615,
                                        616,
                                        617,
                                        618,
                                        619,
                                        620,
                                        620,
                                        621,
                                        621,
                                        621,
                                        622,
                                        622,
                                        622,
                                        623,
                                        623,
                                        623,
                                        624,
                                        624,
                                        625,
                                        2961,
                                        2962,
                                        2963,
                                        2964,
                                        2965,
                                        2966,
                                        2967,
                                        2968,
                                        2969,
                                        2970,
                                        2971)}


def isRewardOptional(tier, rewardId):
    return tier in OptionalRewardTrackDict and rewardId in OptionalRewardTrackDict[tier]


def getItemName(itemId):
    return ItemDict[itemId][0]


def getPluralItemName(itemId):
    return ItemDict[itemId][1]


def avatarHasTrolleyQuest(av):
    return len(av.quests) == 1 and av.quests[0][0] == TROLLEY_QUEST_ID


def avatarHasCompletedTrolleyQuest(av):
    return av.quests[0][4] > 0


def avatarHasFirstCogQuest(av):
    return len(av.quests) == 1 and av.quests[0][0] == FIRST_COG_QUEST_ID


def avatarHasCompletedFirstCogQuest(av):
    return av.quests[0][4] > 0


def avatarHasPhoneQuest(av):
    return len(av.quests) == 1 and av.quests[0][0] == PHONE_QUEST_ID


def avatarHasCompletedPhoneQuest(av):
    return av.quests[0][4] > 0


def avatarWorkingOnRequiredRewards(av):
    tier = av.getRewardTier()
    rewardList = list(getRewardsInTier(tier))
    for i in xrange(len(rewardList)):
        reward_id = rewardList[i]
        actualRewardId = reward_id
        rewardList[i] = actualRewardId

    for questDesc in av.quests:
        questId = questDesc[0]
        rewardId = questDesc[3]
        if rewardId in rewardList:
            return 1
        elif rewardId == NA:
            base_reward_id = getFinalRewardId(questId, fAll=1)
            rewardId = base_reward_id
            if rewardId in rewardList:
                return 1

    return 0


def avatarHasAllRequiredRewards(av, tier):
    rewardHistory = list(av.getRewardHistory()[1])
    rewardList = getRewardsInTier(tier)
    notify.debug('checking avatarHasAllRequiredRewards: history: %s, tier: %s' % (rewardHistory, rewardList))
    for rewardId in rewardList:
        actualRewardId = rewardId
        if actualRewardId in rewardHistory:
            rewardHistory.remove(actualRewardId)
        elif getRewardClass(rewardId) == CogSuitPartReward:
            deptStr = RewardDict.get(rewardId)[1]
            cogPart = RewardDict.get(rewardId)[2]
            dept = ToontownGlobals.cogDept2index[deptStr]
            if av.hasCogPart(cogPart, dept):
                notify.debug(
                    'avatarHasAllRequiredRewards: rewardId: %s counts, avatar has cog part: %s dept: %s' % (
                        actualRewardId, cogPart, dept))
            else:
                notify.debug('avatarHasAllRequiredRewards: CogSuitPartReward: %s not found' % actualRewardId)
                return 0
        else:
            notify.debug('avatarHasAllRequiredRewards: rewardId %s not found' % actualRewardId)
            return 0

    if notify.getDebug():
        notify.debug('avatarHasAllRequiredRewards: remaining rewards: %s' % rewardHistory)
        for rewardId in rewardHistory:
            if not isRewardOptional(tier, rewardId):
                notify.warning('required reward found, expected only optional: %s' % rewardId)

    return 1


def nextQuestList(nextQuest):
    if nextQuest == NA:
        return None
    seqTypes = (types.ListType, types.TupleType)
    if type(nextQuest) in seqTypes:
        return nextQuest
    else:
        return (nextQuest,)
    return None


def checkReward(questId, forked=0):
    quest = QuestDict[questId]
    reward = quest[5]
    nextQuests = nextQuestList(quest[6])
    if nextQuests is None:
        validRewards = RewardDict.keys() + [Any,
                                            AnyCashbotSuitPart,
                                            AnyLawbotSuitPart,
                                            OBSOLETE]
        if reward is OBSOLETE:
            print 'warning: quest %s is obsolete' % questId
        return reward
    else:
        forked = forked or len(nextQuests) > 1
        firstReward = checkReward(nextQuests[0], forked)
        for qId in nextQuests[1:]:
            thisReward = checkReward(qId, forked)

        return firstReward
    return


def assertAllQuestsValid():
    print 'checking quests...'
    for questId in QuestDict.keys():
        try:
            quest = getQuest(questId)
        except AssertionError, e:
            err = 'invalid quest: %s' % questId
            print err
            raise

    for questId in QuestDict.keys():
        quest = QuestDict[questId]
        tier, start, questDesc, fromNpc, toNpc, reward, nextQuest, dialog = quest
        if start:
            checkReward(questId)
