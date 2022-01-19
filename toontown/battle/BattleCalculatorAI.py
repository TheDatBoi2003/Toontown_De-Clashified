from DistributedBattleAI import *
from toontown.battle import SuitBattleGlobals, BattleExperienceAI
from toontown.battle.BattleBase import *
from toontown.battle.BattleBase import NPCSOS, PETSOS
from toontown.battle.SuitBattleGlobals import *
from toontown.pets import PetTricks

HEALING_TRACKS = [HEAL, PETSOS]


class BattleCalculatorAI:
    AccuracyBonuses = [0, 20, 40, 60]
    DamageBonuses = [0, 20, 20, 20]
    DropDamageBonuses = [[0, 20, 30, 40], [0, 30, 40, 50], [0, 40, 50, 60], [0, 50, 60, 70]]
    AttackExpPerTrack = [0, 10, 20, 30, 40, 50, 60, 70]
    NumRoundsLured = AvLureRounds
    NumRoundsSoaked = AvSoakRounds
    TRAP_CONFLICT = -2
    APPLY_HEALTH_ADJUSTMENTS = 1
    TOONS_TAKE_NO_DAMAGE = 0
    CAP_HEALS = 1
    CLEAR_SUIT_ATTACKERS = 1
    SUITS_WAKE_IMMEDIATELY = 1
    FIRST_TRAP_ONLY = 0
    KB_BONUS_LURED_FLAG = 0
    KB_BONUS_TGT_LURED = 1
    notify = DirectNotifyGlobal.directNotify.newCategory('BattleCalculatorAI')
    toonsAlwaysHit = simbase.config.GetBool('toons-always-hit', 0)
    toonsAlwaysMiss = simbase.config.GetBool('toons-always-miss', 0)
    toonsAlways5050 = simbase.config.GetBool('toons-always-5050', 0)
    suitsAlwaysHit = simbase.config.GetBool('suits-always-hit', 0)
    suitsAlwaysMiss = simbase.config.GetBool('suits-always-miss', 0)
    immortalSuits = simbase.config.GetBool('immortal-suits', 0)
    propAndPrestigeStack = simbase.config.GetBool('prop-and-organic-bonus-stack', 0)

# INIT and CLEANUP: Class constructor and destructor ==================================================================
# =====================================================================================================================

    def __init__(self, battle, tutorialFlag=0):
        self.battle = battle
        self.SuitAttackers = {}
        self.trappedSuits = []                      # Keeps track of trapped suits over a longer period of time
        self.trapCollisions = []                    # Keeps track of trap collisions for the current turn
        self.luredSuits = []                        # Keeps track of suit lured over a longer period of time
        self.successfulLures = {}                   # Keeps track of successful lures for the current turn
        self.delayedWakes = []                      # Store cogs that will lose the lure status at the end of the turn
        self.soakedSuits = []                       # Keeps track of soaked suits over a longer period of time
        self.successfulSoaks = {}                   # Keeps track of successful soaks for the current turn
        self.soaksEnded = []                        # Keeps track of soaks that ended for the current turn
        self.lostStatusesDict = {}
        self.toonAtkOrder = []
        self.toonHPAdjusts = {}
        self.toonSkillPtsGained = {}
        self.suitAtkStats = {}
        self.__clearBonuses()
        self.__skillCreditMultiplier = 1
        self.tutorialFlag = tutorialFlag
        self.trainTrapTriggered = False

    def cleanup(self):
        self.battle = None
        return

# PUBLIC ACCESS FUNCTIONS =============================================================================================
# =====================================================================================================================

    def setSkillCreditMultiplier(self, mult):
        self.__skillCreditMultiplier = mult

    def getSkillGained(self, toonId, track):
        return BattleExperienceAI.getSkillGained(self.toonSkillPtsGained, toonId, track)

    def getLuredSuits(self):
        luredSuits = self.luredSuits
        self.notify.debug('Lured suits reported to battle: ' + repr(luredSuits))
        return luredSuits

    def addTrainTrapForJoiningSuit(self, suitId):
        trapInfoToUse = None
        for suit in self.trappedSuits:
            trapStatus = suit.getStatus(SuitStatusNames[2])
            if trapStatus and trapStatus['level'] == RAILROAD_LEVEL_INDEX:
                trapInfoToUse = trapStatus
                break

        if trapInfoToUse:
            self.battle.findSuit(suitId).b_addStatus(trapInfoToUse)
        else:
            self.notify.warning('There is no train trap on %s for some reason!' % suitId)
        return

# BEGIN ROUND CALCULATIONS ============================================================================================
# =====================================================================================================================

    def calculateRound(self):
        longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
        for t in self.battle.activeToons:
            for j in xrange(longest):
                self.battle.toonAttacks[t][TOON_HP_COL].append(-1)
                self.battle.toonAttacks[t][TOON_HPBONUS_COL].append(-1)
                self.battle.toonAttacks[t][TOON_KBBONUS_COL].append(-1)

        for i in xrange(len(self.battle.suitAttacks)):
            for j in xrange(len(self.battle.activeToons)):
                self.battle.suitAttacks[i][SUIT_HP_COL].append(-1)

        self.__initRound()
        for suit in self.battle.activeSuits:
            if suit.isGenerated():
                suit.b_setHP(suit.getHP())

        for suit in self.battle.activeSuits:
            if not hasattr(suit, 'dna'):
                self.notify.warning('a removed suit is in this battle!')
                return None

        self.__calculateToonAttacks()
        self.__postToonStatusRounds()
        self.__calculateSuitAttacks()
        self.__postSuitStatusRounds()
        return None

    def __initRound(self):
        if self.CLEAR_SUIT_ATTACKERS:
            self.SuitAttackers = {}
        self.__findToonAttacks()

        self.notify.debug('Toon attack order: ' + str(self.toonAtkOrder))
        self.notify.debug('Active toons: ' + str(self.battle.activeToons))
        self.notify.debug('Toon attacks: ' + str(self.battle.toonAttacks))
        self.notify.debug('Active suits: ' + str(self.battle.activeSuits))
        self.notify.debug('Suit attacks: ' + str(self.battle.suitAttacks))
        
        self.toonHPAdjusts = {}
        for t in self.battle.activeToons:
            self.toonHPAdjusts[t] = 0

        self.__clearBonuses()
        self.__updateActiveToons()
        self.lostStatusesDict = {}
        self.delayedWakes = []
        self.trainTrapTriggered = False
        self.trapCollisions = []
        self.successfulLures = {}
        self.successfulSoaks = {}
        self.soaksEnded = []
        return

    def __findToonAttacks(self):
        self.toonAtkOrder = []
        attacks = findToonAttack(self.battle.activeToons, self.battle.toonAttacks, PETSOS)
        for atk in attacks:
            self.toonAtkOrder.append(atk[TOON_ID_COL])
        attacks = findToonAttack(self.battle.activeToons, self.battle.toonAttacks, FIRE)
        for atk in attacks:
            self.toonAtkOrder.append(atk[TOON_ID_COL])
        for track in xrange(HEAL, DROP + 1):
            attacks = findToonAttack(self.battle.activeToons, self.battle.toonAttacks, track)
            if track == TRAP:
                sortedTraps = []
                for atk in attacks:
                    if atk[TOON_TRACK_COL] == TRAP:
                        sortedTraps.append(atk)

                for atk in attacks:
                    if atk[TOON_TRACK_COL] == NPCSOS:
                        sortedTraps.append(atk)

                attacks = sortedTraps
            for atk in attacks:
                self.toonAtkOrder.append(atk[TOON_ID_COL])
        specials = findToonAttack(self.battle.activeToons, self.battle.toonAttacks, NPCSOS)
        for special in specials:
            npc_track = NPCToons.getNPCTrack(special[TOON_TGT_COL])
            if npc_track == NPC_TOONS_HIT:
                BattleCalculatorAI.toonsAlwaysHit = 1
            elif npc_track == NPC_COGS_MISS:
                BattleCalculatorAI.suitsAlwaysMiss = 1

    def __calculateToonAttacks(self):
        self.__clearKbBonuses()
        currTrack = None
        maxSuitLevel = 0
        for cog in self.battle.activeSuits:
            maxSuitLevel = max(maxSuitLevel, cog.getActualLevel())

        self.creditLevel = maxSuitLevel
        for toonId in self.toonAtkOrder:
            if self.__getToonHp(toonId) <= 0:
                if self.notify.getDebug():
                    self.notify.debug("Toon %d is dead and can't attack" % toonId)
                continue
            attack = self.battle.toonAttacks[toonId]
            atkTrack = self.__getActualTrack(attack)
            if atkTrack not in [NO_ATTACK, SOS, NPCSOS]:
                if self.notify.getDebug():
                    self.notify.debug('Calculating attack for toon: %d' % toonId)
                isFirstOfCurrentTrack = not currTrack or atkTrack == currTrack
                if self.SUITS_WAKE_IMMEDIATELY and not isFirstOfCurrentTrack:
                    self.__wakeDelayedLures()
                currTrack = atkTrack
                self.__calcToonAttackHp(toonId)
                attackIdx = self.toonAtkOrder.index(toonId)
                self.__handleBonus(attackIdx)
                lastAttack = attackIdx >= len(self.toonAtkOrder) - 1
                if self.__attackHasHit(attack, suit=0) and atkTrack in [THROW, SQUIRT, DROP]:
                    if lastAttack:
                        self.__wakeSuitFromAttack(toonId)
                    else:
                        self.__addSuitToDelayedWake(toonId)
                if lastAttack:
                    self.__wakeDelayedLures()

        self.__processBonuses(self.hpBonuses)
        self.notify.debug('Processing hpBonuses: ' + repr(self.hpBonuses))
        self.__processBonuses(self.kbBonuses)
        self.notify.debug('Processing kbBonuses: ' + repr(self.kbBonuses))
        self.__postProcessToonAttacks()
        return

    def __postToonStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(SuitStatusNames[0])
            if removedStatus:
                self.__removeLureStatus(activeSuit, removedStatus)

    def __postSuitStatusRounds(self):
        for activeSuit in self.battle.activeSuits:
            removedStatus = activeSuit.decStatusRounds(SuitStatusNames[1])
            if removedStatus:
                self.__removeSoakStatus(activeSuit, removedStatus)

            removedStatus = activeSuit.decStatusRounds(SuitStatusNames[3])
            if removedStatus:
                self.__removeStatus(activeSuit, removedStatus)

    def __updateActiveToons(self):
        if self.notify.getDebug():
            self.notify.debug('updateActiveToons()')
        if not self.CLEAR_SUIT_ATTACKERS:
            oldSuitIds = []
            for s in self.SuitAttackers.keys():
                for t in self.SuitAttackers[s].keys():
                    if t not in self.battle.activeToons:
                        del self.SuitAttackers[s][t]
                        if len(self.SuitAttackers[s]) == 0:
                            oldSuitIds.append(s)

            for oldSuitId in oldSuitIds:
                del self.SuitAttackers[oldSuitId]
                
        for suit in self.luredSuits:
            lureStatus = suit.getStatus(SuitStatusNames[0])
            for toon in lureStatus['toons']:
                if toon != -1 and toon not in self.battle.activeToons:
                    lureIndex = lureStatus['toons'].index(toon)
                    self.notify.debug('Lure for ' + str(toon) + ' will no longer give exp')
                    lureStatus['toons'][lureIndex] = -1

        for suit in self.trappedSuits:
            trapStatus = suit.getStatus(SuitStatusNames[2])
            if trapStatus['toon'] not in self.battle.activeToons:
                self.notify.debug('Trap for toon ' + str(trapStatus['toon']) + ' will no longer give exp')
                trapStatus['toon'] = 0

# TOON ACCURACY CALCULATION ===========================================================================================

    def __calcToonAtkHit(self, attackIndex, atkTargets):
        toon = self.battle.getToon(attackIndex)
        if len(atkTargets) == 0:
            return 0
        if toon.getInstaKill() or toon.getAlwaysHitSuits():
            return 1
        if self.tutorialFlag:
            return 1
        if self.toonsAlways5050:
            return random.randint(0, 1)
        if self.toonsAlwaysHit:
            return 1
        elif self.toonsAlwaysMiss:
            return 0

        debug = self.notify.getDebug()
        attack = self.battle.toonAttacks[attackIndex]
        atkTrack, atkLevel = self.__getActualTrackLevel(attack)
        if atkTrack == NPCSOS or atkTrack == FIRE:
            return 1
        if atkTrack == TRAP:
            attack[TOON_ACCBONUS_COL] = 0
            return 1
        elif atkTrack == PETSOS:
            return self.__calculatePetTrickSuccess(attack)

        tgtDef = 0
        numLured = 0
        if atkTrack not in HEALING_TRACKS:
            numLured, tgtDef = self.__findLowestDefense(atkTargets, numLured, tgtDef)

        trackExp = self.__checkTrackAccBonus(attack[TOON_ID_COL], atkTrack)
        trackExp = self.__findHighestTrackBonus(atkTrack, attack, trackExp)

        propAcc = AvPropAccuracy[atkTrack][atkLevel]

        if atkTrack in ACC_UP_TRACKS:
            prestige = self.__getToonPrestige(attack[TOON_ID_COL], atkTrack)
            propBonus = self.__getToonPropBonus(atkTrack)
            if self.propAndPrestigeStack:
                propAcc = 0
                if prestige:
                    self.notify.debug('using track bonus accuracy')
                    propAcc += AvBonusAccuracy[atkTrack][atkLevel] - AvPropAccuracy[atkTrack][atkLevel]
                if propBonus:
                    self.notify.debug('using prop bonus accuracy')
                    propAcc += AvBonusAccuracy[atkTrack][atkLevel] - AvPropAccuracy[atkTrack][atkLevel]
            elif prestige or propBonus:
                self.notify.debug('using track OR prop bonus accuracy')
                propAcc = AvBonusAccuracy[atkTrack][atkLevel]

        attackAcc = propAcc + trackExp + tgtDef

        currAtk = self.toonAtkOrder.index(attackIndex)
        if currAtk > 0 and atkTrack != HEAL:
            prevAtkTrack, prevAttack = self.__getPreviousAttack(currAtk)
            if (atkTrack == prevAtkTrack and (attack[TOON_TGT_COL] == prevAttack[TOON_TGT_COL]
                                              or atkTrack == LURE
                                              and self.__targetIsLured(atkLevel, atkTrack, attack))):
                if prevAttack[TOON_ACCBONUS_COL]:
                    self.notify.debug('DODGE: Toon attack track dodged')
                else:
                    self.notify.debug('HIT: Toon attack track hit')
                attack[TOON_ACCBONUS_COL] = prevAttack[TOON_ACCBONUS_COL]
                return not attack[TOON_ACCBONUS_COL]

        atkAccResult = attackAcc
        self.notify.debug('setting atkAccResult to %d' % atkAccResult)
        acc = attackAcc + self.__calcToonAccBonus(attackIndex)
        if atkTrack != LURE and atkTrack != HEAL:
            if atkTrack == DROP and numLured == len(atkTargets):
                self.notify.debug('all targets are lured, attack misses')
                attack[TOON_ACCBONUS_COL] = 0
                return 0
            else:
                if numLured == len(atkTargets):
                    self.notify.debug('all targets are lured, attack hits')
                    attack[TOON_ACCBONUS_COL] = 0
                    return 1
                else:
                    luredRatio = float(numLured) / float(len(atkTargets))
                    accAdjust = 100 * luredRatio
                    if accAdjust > 0 and debug:
                        self.notify.debug(
                            str(numLured) + ' out of ' + str(len(atkTargets)) + ' targets are lured, so adding ' + str(
                                accAdjust) + ' to attack accuracy')
                    acc += accAdjust
        if acc > MaxToonAcc:
            acc = MaxToonAcc
        if attack[TOON_TRACK_COL] == NPCSOS:
            randChoice = 0
        else:
            randChoice = random.randint(0, 99)
        if randChoice < acc:
            self.notify.debug('HIT: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            attack[TOON_ACCBONUS_COL] = 0
        else:
            self.notify.debug('MISS: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            attack[TOON_ACCBONUS_COL] = 1
        return not attack[TOON_ACCBONUS_COL]

    def __findLowestDefense(self, atkTargets, numLured, tgtDef):
        for currTarget in atkTargets:
            thisSuitDef = self.__getTargetDefense(currTarget)
            self.notify.debug('Examining suit def for toon attack: ' + str(thisSuitDef))
            tgtDef = min(thisSuitDef, tgtDef)
            if currTarget.getStatus(SuitStatusNames[0]):
                numLured += 1
        self.notify.debug('Suit defense used for toon attack: ' + str(tgtDef))
        return numLured, tgtDef

    @staticmethod
    def __getTargetDefense(suit):
        suitDef = SuitBattleGlobals.SuitAttributes[suit.dna.name]['def'][suit.getLevel()]
        suitDef += 5 * suit.isExecutive
        for status in suit.statuses:
            if 'defense' in status:
                suitDef += status['defense']
        return -suitDef

    def __calcToonAccBonus(self, attackKey):
        numPrevHits = 0
        attackIdx = self.toonAtkOrder.index(attackKey)
        for currPrevAtk in xrange(attackIdx - 1, -1, -1):
            attack = self.battle.toonAttacks[attackKey]
            atkTrack, atkLevel = self.__getActualTrackLevel(attack)
            prevAttackKey = self.toonAtkOrder[currPrevAtk]
            prevAttack = self.battle.toonAttacks[prevAttackKey]
            prvAtkTrack, prvAtkLevel = self.__getActualTrackLevel(prevAttack)
            if (self.__attackHasHit(prevAttack)
                    and (attackAffectsGroup(prvAtkTrack, prvAtkLevel, prevAttack[TOON_TRACK_COL])
                         or attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL])
                         or attack[TOON_TGT_COL] == prevAttack[TOON_TGT_COL])
                    and atkTrack != prvAtkTrack):
                numPrevHits += 1

        if numPrevHits > 0:
            self.notify.debug('ACC BONUS: toon attack received accuracy bonus of ' +
                              str(self.AccuracyBonuses[numPrevHits]) + ' from previous attack')
        return self.AccuracyBonuses[numPrevHits]

    def __findHighestTrackBonus(self, atkTrack, attack, trackExp):
        for currOtherAtk in self.toonAtkOrder:
            if currOtherAtk != attack[TOON_ID_COL]:
                nextAttack = self.battle.toonAttacks[currOtherAtk]
                nextAtkTrack = self.__getActualTrack(nextAttack)
                if atkTrack == nextAtkTrack and attack[TOON_TGT_COL] == nextAttack[TOON_TGT_COL]:
                    currTrackExp = self.__checkTrackAccBonus(nextAttack[TOON_ID_COL], atkTrack)
                    self.notify.debug('Examining toon track exp bonus: ' + str(currTrackExp))
                    trackExp = max(currTrackExp, trackExp)
        self.notify.debug('Toon track exp bonus used for toon attack: ' + str(trackExp))
        return trackExp

    def __checkTrackAccBonus(self, toonId, track):
        toon = self.battle.getToon(toonId)
        if toon:
            toonExpLvl = toon.experience.getExpLevel(track)
            exp = self.AttackExpPerTrack[toonExpLvl]
            if track == HEAL:
                exp = exp * 0.5
            self.notify.debug('Toon track exp: ' + str(toonExpLvl) + ' and resulting acc bonus: ' + str(exp))
            return exp
        else:
            return 0

    def __getPreviousAttack(self, currAtk):
        prevAtkId = self.toonAtkOrder[currAtk - 1]
        prevAttack = self.battle.toonAttacks[prevAtkId]
        prevAtkTrack = self.__getActualTrack(prevAttack)
        return prevAtkTrack, prevAttack

    def __targetIsLured(self, atkLevel, atkTrack, attack):
        return (not attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL])
                and attack[TOON_TGT_COL] in self.successfulLures
                or attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL]))

# TOON DAMAGE/SUCCESS CALCULATION =====================================================================================

    def __calcToonAttackHp(self, toonId):
        attack = self.battle.toonAttacks[toonId]
        targetList = self.__createToonTargetList(toonId)
        atkHit = self.__calcToonAtkHit(toonId, targetList)
        atkTrack, atkLevel, atkHp = self.__getActualTrackLevelHp(attack)
        if not atkHit and atkTrack != HEAL:
            return
        targetExists = 0
        toon = self.battle.getToon(toonId)
        for target in targetList:
            attackLevel = -1
            result = 0
            npcSOS = atkTrack == NPCSOS
            kbBonuses = attack[TOON_KBBONUS_COL]
            if atkTrack == PETSOS:
                result, targetExists = atkHp, self.__getToonHp(target) <= 0
            elif atkTrack == FIRE:
                result, targetExists = self.__doFireCalc(target, toon)
            elif atkTrack == HEAL:
                result, targetExists = self.__doHealCalc(atkHp, atkLevel, atkTrack, attack, npcSOS,
                                                         target, len(targetList), toon)
            elif atkTrack == TRAP:
                result, targetExists = self.__doTrapCalc(atkHp, atkLevel, kbBonuses, npcSOS,
                                                         target, targetList, toonId)
            elif atkTrack == LURE:
                result, targetExists = self.__doLureCalc(atkLevel, attack, attackLevel, result, target, toonId)
            elif atkTrack == SOUND:
                result, targetExists = self.__doSoundCalc(atkHp, atkLevel, atkTrack, kbBonuses, npcSOS, target, toon)
            elif atkTrack == SQUIRT:
                result, targetExists = self.__doSquirtCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)
            elif atkTrack == DROP:
                result, targetExists = self.__doDropCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)
            else:
                result, targetExists = self.__doAttackCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)

            self.notify.info('%d targets %s, result: %d' % (toonId, target, result))

            if result != 0:
                targets = self.__getToonTargets(attack)
                if target not in targets:
                    self.notify.debug("The toon's target is not accessible!")
                    continue

                if result > 0 and target in self.luredSuits:
                    for currInfo in self.__getLuredExpInfo(target):
                        self.notify.debug('Giving lure EXP to toon ' + str(currInfo[0]))
                        self.__addAttackExp(attack, LURE, currInfo[1], currInfo[0])
                    if atkTrack == LURE:
                        self.__removeLureStatus(target)

                attack[TOON_HP_COL][targets.index(target)] = result  # <--------  THIS IS THE ATTACK OUTPUT!

        if not targetExists and self.__prevAtkTrack(toonId) != atkTrack:
            self.notify.info('Something happened to our target!  Removing attack...')
            self.__clearAttack(toonId)
        return

    # noinspection PyMethodMayBeStatic
    def __doFireCalc(self, target, toon):
        result = 0
        if target:
            costToFire = 1
            abilityToFire = toon.getPinkSlips()
            toon.removePinkSlips(costToFire)
            if costToFire <= abilityToFire:
                target.skeleRevives = 0
                result = target.getHP()
        return result, target.getHP() > 0

    def __doHealCalc(self, atkHp, atkLevel, atkTrack, attack, npcSOS, target, targetCount, toon):
        result = self.__doDamageCalc(atkHp, atkLevel, atkTrack, npcSOS, toon)
        if not self.__attackHasHit(attack, suit=0):
            result = result * 0.2
        if self.notify.getDebug():
            self.notify.debug('toon does ' + str(result) + ' healing to toon(s)')
        result = result / targetCount
        self.notify.debug('Splitting heal among targets')
        return result, self.__getToonHp(target) > 0

    def __doTrapCalc(self, atkHp, atkLevel, kbBonuses, npcSOS, target, targetList, toonId):
        npcDamage = 0
        targetId = target.getDoId()
        if npcSOS:
            npcDamage = atkHp

        if self.FIRST_TRAP_ONLY and self.__getSuitTrapType(target) != NO_TRAP:
            self.__clearAttack(toonId)
        if atkLevel == RAILROAD_LEVEL_INDEX:
            result = self.__groupTrapSuits(target, atkLevel, toonId, targetList, npcDamage)
            if target.getStatus(SuitStatusNames[0]):
                self.notify.debug('Train Trap on lured suit %d, \n indicating with KB_BONUS_COL flag' % targetId)
                tgtPos = self.battle.activeSuits.index(target)
                kbBonuses[tgtPos] = self.KB_BONUS_LURED_FLAG
        else:
            result = self.__trapSuit(target, atkLevel, toonId, npcDamage)
        return result, target.getHP() > 0

    def __doLureCalc(self, atkLevel, attack, attackLevel, result, suit, toonId):
        self.notify.debug('Suit lured, but no trap exists')
        targetLured, validTargetAvail = self.__lureSuit(atkLevel, attack, suit, toonId)
        suitId = suit.getDoId()
        if self.__getSuitTrapType(suit) != NO_TRAP:
            attackDamage, attackLevel, trapCreatorId = self.__getTrapInfo(suit)
            if trapCreatorId > 0:
                self.notify.debug('Giving trap EXP to toon ' + str(trapCreatorId))
                self.__addAttackExp(attack, TRAP, attackLevel, trapCreatorId)
            self.__clearTrapCreator(trapCreatorId, suit)
            self.notify.debug('Suit lured right onto a trap! (%s,%s)' % (AvProps[TRAP][attackLevel], attackLevel))
            result = attackDamage
            self.__removeTrapStatus(suit)

        if targetLured:
            lures = self.successfulLures
            if suitId not in lures:
                lures[suitId] = [atkLevel, toonId, result]
        if attackLevel == -1:
            result = LURE_SUCCEEDED
        return result, validTargetAvail

    def __doSoundCalc(self, atkHp, atkLevel, atkTrack, kbBonuses, npcSOS, target, toon):
        if target.getStatus(SuitStatusNames[0]) and atkTrack == SOUND:
            self.notify.debug('Sound on lured suit, ' + 'indicating with KB_BONUS_COL flag')
            tgtPos = self.battle.activeSuits.index(target)
            kbBonuses[tgtPos] = self.KB_BONUS_LURED_FLAG
            self.__addSuitToDelayedWake(toon.getDoId(), target)
        return self.__doAttackCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)

    def __doSquirtCalc(self, atkHp, atkLevel, atkTrack, npcSOS, target, toon):
        self.__soakSuit(atkLevel, toon, target)
        if toon.checkTrackPrestige(SQUIRT):
            activeSuits = self.battle.activeSuits
            suitIndex = activeSuits.index(target)
            adjacentSuits = []
            if suitIndex - 1 >= 0:
                adjacentSuits.append(activeSuits[suitIndex - 1])
            if suitIndex + 1 < len(activeSuits):
                adjacentSuits.append(activeSuits[suitIndex + 1])
            for suit in adjacentSuits:
                self.__soakSuit(atkLevel, toon, suit)
        return self.__doAttackCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)

    def __doDropCalc(self, atkHp, atkLevel, atkTrack, npcSOS, target, toon):
        if target.getStatus(SuitStatusNames[0]):
            result, validTargetAvail = 0, 0
            self.notify.debug('setting damage to 0, since drop on a lured suit')
        else:
            result, validTargetAvail = self.__doAttackCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon)
        return result, validTargetAvail

    def __doAttackCalc(self, atkHp, atkLevel, atkTrack, npcSOS, target, toon):
        return self.__doInstaKillCalc(atkHp, atkLevel, atkTrack, npcSOS, target, toon), target.getHP() > 0

    def __doInstaKillCalc(self, atkHp, atkLevel, atkTrack, npcSOS, target, toon):
        if toon and toon.getInstaKill():
            attackDamage = target.getHP()
        else:
            attackDamage = self.__doDamageCalc(atkHp, atkLevel, atkTrack, npcSOS, toon)
        return attackDamage

    def __doDamageCalc(self, atkHp, atkLevel, atkTrack, npcSOS, toon):
        if npcSOS:
            damage = atkHp
        else:
            damage = getAvPropDamage(atkTrack, atkLevel, toon.experience.getExp(atkTrack),
                                     toon.checkTrackPrestige(atkTrack), self.__getToonPropBonus(atkTrack),
                                     self.propAndPrestigeStack)
        return damage

    def __getToonPrestige(self, toonId, track):
        toon = self.battle.getToon(toonId)
        if toon:
            return toon.checkTrackPrestige(track)
        else:
            return False

    def __getToonPropBonus(self, track):
        return self.battle.getInteractivePropTrackBonus() == track

    def __clearAttack(self, attackIdx, toon=1):
        if toon:
            if self.notify.getDebug():
                self.notify.debug('clearing out toon attack for toon ' + str(attackIdx) + '...')
            self.battle.toonAttacks[attackIdx] = getToonAttack(attackIdx)
            longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
            for j in xrange(longest):
                self.battle.toonAttacks[attackIdx][TOON_HP_COL].append(-1)
                self.battle.toonAttacks[attackIdx][TOON_HPBONUS_COL].append(-1)
                self.battle.toonAttacks[attackIdx][TOON_KBBONUS_COL].append(-1)

            if self.notify.getDebug():
                self.notify.debug('toon attack is now ' + repr(self.battle.toonAttacks[attackIdx]))
        else:
            self.notify.warning('__clearAttack not implemented for suits!')

    def __postProcessToonAttacks(self):
        self.notify.debug('__postProcessToonAttacks()')
        lastTrack = -1
        lastAttacks = []
        self.__clearHpBonuses()
        for currentToon in self.toonAtkOrder:
            if currentToon != -1:
                attack = self.battle.toonAttacks[currentToon]
                atkTrack, atkLevel = self.__getActualTrackLevel(attack)
                if atkTrack not in [HEAL, NO_ATTACK] + SOS_TRACKS:
                    targets = self.__createToonTargetList(currentToon)
                    allTargetsDead = 1
                    for suit in targets:
                        damageDone = self.__getToonAttackDamage(attack)
                        if damageDone > 0:
                            self.__rememberToonAttack(suit.getDoId(), attack[TOON_ID_COL], damageDone)
                        if atkTrack == TRAP:
                            if suit in self.trappedSuits:
                                trapInfo = suit.getStatus(SuitStatusNames[2])
                                suit.battleTrap = trapInfo['level']
                        targetDead = 0
                        if suit.getHP() > 0:
                            allTargetsDead = 0
                        else:
                            targetDead = 1
                            if atkTrack != LURE:
                                for currLastAtk in lastAttacks:
                                    self.__clearTgtDied(suit, currLastAtk, attack)

                        tgtId = suit.getDoId()
                        if tgtId in self.successfulLures and atkTrack == LURE:
                            lureInfo = self.successfulLures[tgtId]
                            self.notify.debug('applying lure data: ' + repr(lureInfo))
                            tgtPos = self.battle.activeSuits.index(suit)
                            if suit in self.trappedSuits:
                                trapInfo = suit.getStatus(SuitStatusNames[2])
                                if trapInfo['level'] == RAILROAD_LEVEL_INDEX:
                                    self.notify.debug('train trap triggered for %d' % suit.doId)
                                    self.trainTrapTriggered = True
                                self.__removeTrapStatus(suit)
                            attack[TOON_KBBONUS_COL][tgtPos] = self.KB_BONUS_TGT_LURED
                            attack[TOON_HP_COL][tgtPos] = lureInfo[2]
                        elif suit.getStatus(SuitStatusNames[0]) and atkTrack == DROP:
                            tgtPos = self.battle.activeSuits.index(suit)
                            attack[TOON_KBBONUS_COL][tgtPos] = self.KB_BONUS_LURED_FLAG
                        if targetDead and atkTrack != lastTrack:
                            tgtPos = self.battle.activeSuits.index(suit)
                            attack[TOON_HP_COL][tgtPos] = 0
                            attack[TOON_KBBONUS_COL][tgtPos] = -1

                    if allTargetsDead and atkTrack != lastTrack:
                        if self.notify.getDebug():
                            self.notify.debug('all targets of toon attack ' + str(currentToon) + ' are dead')
                        self.__clearAttack(currentToon, toon=1)
                        attack = self.battle.toonAttacks[currentToon]
                        atkTrack, atkLevel = self.__getActualTrackLevel(attack)
                damagesDone = self.__applyToonAttackDamages(currentToon)
                if atkTrack != LURE:
                    self.__applyToonAttackDamages(currentToon, hpBonus=1)
                    if atkTrack in [THROW, SQUIRT]:
                        self.__applyToonAttackDamages(currentToon, kbBonus=1)
                if lastTrack != atkTrack:
                    lastAttacks = []
                    lastTrack = atkTrack
                lastAttacks.append(attack)
                if atkTrack != PETSOS and atkLevel < self.creditLevel:
                    if atkTrack in [TRAP, LURE]:
                        pass
                    elif atkTrack == HEAL:
                        if damagesDone != 0:
                            self.__addAttackExp(attack)
                    else:
                        self.__addAttackExp(attack)

        if self.trainTrapTriggered:
            for suit in self.battle.activeSuits:
                suitId = suit.doId
                self.__removeTrapStatus(suit)
                suit.battleTrap = NO_TRAP
                self.notify.debug('train trap triggered, removing trap from %d' % suitId)

        if self.notify.getDebug():
            for currentToon in self.toonAtkOrder:
                attack = self.battle.toonAttacks[currentToon]
                self.notify.debug('Final Toon attack: ' + str(attack))

    def __rememberToonAttack(self, suitId, toonId, damage):
        if suitId not in self.SuitAttackers:
            self.SuitAttackers[suitId] = {toonId: damage}
        else:
            if toonId not in self.SuitAttackers[suitId]:
                self.SuitAttackers[suitId][toonId] = damage
            else:
                if self.SuitAttackers[suitId][toonId] <= damage:
                    self.SuitAttackers[suitId] = [
                        toonId, damage]

    def __applyToonAttackDamages(self, toonId, hpBonus=0, kbBonus=0):
        totalDamages = 0
        if not self.APPLY_HEALTH_ADJUSTMENTS:
            return totalDamages
        attack = self.battle.toonAttacks[toonId]
        track = self.__getActualTrack(attack)
        if track not in [NO_ATTACK, SOS, TRAP, NPCSOS]:
            targets = self.__getToonTargets(attack)
            for position in xrange(len(targets)):
                targetList = self.__createToonTargetList(toonId)
                target = targets[position]
                if hpBonus:
                    if target in targetList:
                        damageDone = attack[TOON_HPBONUS_COL][position]
                    else:
                        damageDone = 0
                elif kbBonus:
                    if target in targetList:
                        damageDone = attack[TOON_KBBONUS_COL][position]
                    else:
                        damageDone = 0
                else:
                    damageDone = attack[TOON_HP_COL][position]
                if damageDone <= 0 or self.immortalSuits:
                    continue
                if track in HEALING_TRACKS:
                    target = target
                    if self.CAP_HEALS:
                        toonHp = self.__getToonHp(target)
                        toonMaxHp = self.__getToonMaxHp(target)
                        if toonHp + damageDone > toonMaxHp:
                            damageDone = toonMaxHp - toonHp
                            attack[TOON_HP_COL][position] = damageDone
                    self.toonHPAdjusts[target] += damageDone
                    totalDamages = totalDamages + damageDone
                    continue

                target.setHP(target.getHP() - damageDone)

                targetId = target.getDoId()
                if hpBonus:
                    self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage from HP-Bonus')
                elif kbBonus:
                    self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage from KB-Bonus')
                else:
                    self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage')
                totalDamages = totalDamages + damageDone
                if target.getHP() <= 0:
                    if target.getSkeleRevives() >= 1:
                        target.useSkeleRevive()
                        attack[SUIT_REVIVE_COL] = attack[SUIT_REVIVE_COL] | 1 << position
                    else:
                        self.suitLeftBattle(target)
                        attack[SUIT_DIED_COL] = attack[SUIT_DIED_COL] | 1 << position
                        self.notify.debug('Suit' + str(targetId) + 'bravely expired in combat')

        return totalDamages

    @staticmethod
    def __getToonAttackDamage(attack):
        mostDamage = 0
        for hp in attack[TOON_HP_COL]:
            if hp > mostDamage:
                mostDamage = hp
        return mostDamage

# TOON DAMAGE BONUS CALCULATION =======================================================================================

    def __clearBonuses(self):
        self.__clearHpBonuses()
        self.__clearKbBonuses()

    def __clearHpBonuses(self):
        self.hpBonuses = [{} for _ in xrange(len(self.battle.activeSuits))]

    def __clearKbBonuses(self):
        self.kbBonuses = [{} for _ in xrange(len(self.battle.activeSuits))]

    def __handleBonus(self, attackIdx):
        attackerId = self.toonAtkOrder[attackIdx]
        attack = self.battle.toonAttacks[attackerId]
        atkDmg = self.__getToonAttackDamage(attack)
        atkTrack = self.__getActualTrack(attack)
        if atkTrack != LURE or atkDmg > 0:
            self.__addDmgToBonuses(attackIdx)
            if atkTrack in [THROW, SQUIRT]:
                self.__addDmgToBonuses(attackIdx, hp=0)

    def __processBonuses(self, bonuses):
        hpBonus = bonuses == self.hpBonuses
        targetPos = 0
        for bonusTarget in bonuses:
            for currAtkType in bonusTarget.keys():
                currentAttacks = bonusTarget[currAtkType]
                attackCount = len(currentAttacks)
                if attackCount > 1 or not hpBonus and attackCount > 0:
                    totalDamages = 0
                    for currentDamage in currentAttacks:
                        totalDamages += currentDamage[1]

                    attackIdx = currentAttacks[attackCount - 1][0]
                    attackerId = self.toonAtkOrder[attackIdx]
                    attack = self.battle.toonAttacks[attackerId]

                    def getOrgToons(toons, track):
                        numOrgs = 0
                        for toonId in toons:
                            if self.battle.getToon(toonId).checkTrackPrestige(track):
                                numOrgs += 1
                        return numOrgs

                    if hpBonus:
                        if targetPos < len(attack[TOON_HPBONUS_COL]):
                            if attack[TOON_TRACK_COL] == DROP:
                                numOrgs = getOrgToons(self.battle.activeToons, DROP)
                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (self.DropDamageBonuses[numOrgs][attackCount - 1] * 0.01))
                            else:
                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (self.DamageBonuses[attackCount - 1] * 0.01))
                            self.notify.debug('Applying hp bonus to track ' +
                                              str(attack[TOON_TRACK_COL]) + ' of ' +
                                              str(attack[TOON_HPBONUS_COL][targetPos]))
                    elif len(attack[TOON_KBBONUS_COL]) > targetPos:
                        kbBonus = 0.5
                        for suit in self.lostStatusesDict[SuitStatusNames[0]].keys():
                            if self.battle.activeSuits[targetPos] == suit:
                                kbBonus = self.lostStatusesDict[SuitStatusNames[0]][suit]['kbBonus']
                        attack[TOON_KBBONUS_COL][targetPos] = math.ceil(totalDamages * kbBonus)
                        if self.notify.getDebug():
                            self.notify.debug('Applying kb bonus to track %s of %s to target %s' %
                                              (attack[TOON_TRACK_COL], attack[TOON_KBBONUS_COL][targetPos], targetPos))
                    else:
                        self.notify.warning('invalid tgtPos for knock back bonus: %d' % targetPos)

            targetPos += 1

        if hpBonus:
            self.__clearHpBonuses()
        else:
            self.__clearKbBonuses()

    def __addDmgToBonuses(self, attackIndex, hp=1):
        toonId = self.toonAtkOrder[attackIndex]
        attack = self.battle.toonAttacks[toonId]
        atkTrack = self.__getActualTrack(attack)
        if atkTrack == HEAL or atkTrack == PETSOS:
            return
        targets = self.__createToonTargetList(toonId)
        for currTgt in targets:
            tgtPos = self.battle.suits.index(currTgt)
            dmg = attack[TOON_HP_COL][tgtPos]
            if hp:
                self.__addBonus(attackIndex, self.hpBonuses[tgtPos], dmg, atkTrack)
                self.notify.info(self.hpBonuses)
            elif currTgt.getStatus(SuitStatusNames[0]):
                self.__addBonus(attackIndex, self.kbBonuses[tgtPos], dmg, atkTrack)

    @staticmethod
    def __addBonus(attackIndex, bonusTarget, dmg, track):
        if track in bonusTarget:
            bonusTarget[track].append((attackIndex, dmg))
        else:
            bonusTarget[track] = [(attackIndex, dmg)]

    def __bonusExists(self, tgtSuit, hp=1):
        tgtPos = self.battle.activeSuits.index(tgtSuit)
        if hp:
            bonusLen = len(self.hpBonuses[tgtPos])
        else:
            bonusLen = len(self.kbBonuses[tgtPos])
        if bonusLen > 0:
            return 1
        return 0

# TARGETING CALCULATION ===============================================================================================

    def __createToonTargetList(self, attackIndex):
        attack = self.battle.toonAttacks[attackIndex]
        atkTrack, atkLevel = self.__getActualTrackLevel(attack)
        targetList = []
        if atkTrack == NPCSOS:
            return targetList
        if not attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL]):
            if atkTrack == HEAL:
                target = attack[TOON_TGT_COL]
            else:
                target = self.battle.findSuit(attack[TOON_TGT_COL])
            if target:
                targetList.append(target)
        else:
            if atkTrack in HEALING_TRACKS:
                if attack[TOON_TRACK_COL] == NPCSOS or atkTrack == PETSOS:
                    targetList = self.battle.activeToons
                else:
                    for currToon in self.battle.activeToons:
                        if attack[TOON_ID_COL] != currToon:
                            targetList.append(currToon)

            else:
                targetList = self.battle.activeSuits
        return targetList

    def __clearTgtDied(self, tgt, lastAtk, currAtk):
        position = self.battle.activeSuits.index(tgt)
        currAtkTrack = self.__getActualTrack(currAtk)
        lastAtkTrack = self.__getActualTrack(lastAtk)
        if currAtkTrack == lastAtkTrack and lastAtk[SUIT_DIED_COL] & 1 << position and self.__attackHasHit(currAtk,
                                                                                                           suit=0):
            if self.notify.getDebug():
                self.notify.debug('Clearing suit died for ' + str(tgt.getDoId()) + ' at position ' + str(
                    position) + ' from toon attack ' + str(lastAtk[TOON_ID_COL]) + ' and setting it for ' + str(
                    currAtk[TOON_ID_COL]))
            lastAtk[SUIT_DIED_COL] = lastAtk[SUIT_DIED_COL] ^ 1 << position
            self.suitLeftBattle(tgt)
            currAtk[SUIT_DIED_COL] = currAtk[SUIT_DIED_COL] | 1 << position

    def __getToonTargets(self, attack):
        track = self.__getActualTrack(attack)
        if track in HEALING_TRACKS:
            return self.battle.activeToons
        else:
            return self.battle.activeSuits

    def __allTargetsDead(self, attackIdx, toon=1):
        allTargetsDead = 1
        if toon:
            targets = self.__createToonTargetList(attackIdx)
            for currTgt in targets:
                if currTgt.getHp() > 0:
                    allTargetsDead = 0
                    break

        else:
            self.notify.warning('__allTargetsDead: suit ver. not implemented!')
        return allTargetsDead

# EXPERIENCE CALCULATION ==============================================================================================

    def __addAttackExp(self, attack, attackTrack=-1, attackLevel=-1, attackerId=-1):
        track = -1
        level = -1
        toonId = -1
        if attackTrack != -1 and attackLevel != -1 and attackerId != -1:
            track = attackTrack
            level = attackLevel
            toonId = attackerId
        elif self.__attackHasHit(attack):
            self.notify.debug('Attack ' + repr(attack) + ' has hit')
            track = attack[TOON_TRACK_COL]
            level = attack[TOON_LVL_COL]
            toonId = attack[TOON_ID_COL]
        if track != -1 and track not in [NPCSOS, PETSOS] and level != -1 and toonId != -1:
            expList = self.toonSkillPtsGained.get(toonId, None)
            if expList is None:
                expList = [0] * len(Tracks)
                self.toonSkillPtsGained[toonId] = expList
            expList[track] = min(ExperienceCap, expList[track] + (level + 1) * self.__skillCreditMultiplier)
            self.notify.info('%s gained %d %s EXP, current exp: %d' %
                             (toonId, (level + 1) * self.__skillCreditMultiplier, Tracks[track], expList[track]))
        return

# TRAP STATUS CALCULATION =============================================================================================

    def __trapSuit(self, suit, trapLvl, attackerId, npcDamage=0):
        if not npcDamage:
            if suit.getStatus(SuitStatusNames[2]):
                self.__checkTrapConflict(suit.doId)
            else:
                self.__applyTrap(attackerId, suit, trapLvl)
        else:
            self.__applyNPCTrap(npcDamage, suit, trapLvl)

        if suit.doId in self.trapCollisions:
            self.notify.info('There were two traps that collided! Removing the traps now.')
            self.__removeTrapStatus(suit)
            result = 0
        else:
            result = SuitStatusNames[2] in suit.statuses
        return result

    def __groupTrapSuits(self, suit, trapLvl, attackerId, allSuits, npcDamage=0):
        suitId = suit.getDoId()
        if not npcDamage:
            if suit.getStatus(SuitStatusNames[2]):
                self.__checkTrapConflict(suitId, allSuits)
            else:
                self.__applyTrap(attackerId, suitId, trapLvl)
                self.__addSuitToDelayedWake(attackerId, ignoreDamageCheck=True)
        else:
            self.__applyNPCTrap(npcDamage, suit, trapLvl)

        if suit in self.trapCollisions:
            result = 0
        else:
            result = SuitStatusNames[2] in suit.statuses
        return result

    def __applyTrap(self, toonId, suit, trapLvl):
        toon = self.battle.getToon(toonId)
        damage = getTrapPropDamage(trapLvl, toon, suit)
        self.notify.info('%s places a %s damage trap!' % (toonId, damage))
        if trapLvl < self.creditLevel:
            self.__addTrapStatus(suit, trapLvl, damage, toonId)
        else:
            self.__addTrapStatus(suit, trapLvl, damage)

    def __applyNPCTrap(self, npcDamage, suit, trapLvl):
        self.notify.info('An NPC places a trap!')
        if suit in self.trapCollisions:
            self.__addTrapStatus(suit, trapLvl, npcDamage)
        else:
            if not suit.getStatus(SuitStatusNames[0]):
                self.__addTrapStatus(suit, trapLvl, npcDamage)

    def __addTrapStatus(self, suit, level=-1, damage=0, toonId=-1):
        trapStatus = getSuitStatus(SuitStatusNames[2])
        trapStatus['level'] = level
        trapStatus['damage'] = damage
        trapStatus['toon'] = toonId
        self.notify.info('%s now has a level %d trap that deals %d damage.' % (suit.doId, level, damage))
        suit.b_addStatus(trapStatus)
        self.trappedSuits.append(suit)

    def __checkTrapConflict(self, suitId, allSuits=None):
        if suitId not in self.trapCollisions:
            self.trapCollisions.append(suitId)
        if allSuits:
            for suit in allSuits:
                if suit.getStatus(SuitStatusNames[2]) and suit.doId not in self.trapCollisions:
                    self.trapCollisions.append(suitId)

    def __removeTrapStatus(self, suit):
        if suit in self.trappedSuits:
            self.trappedSuits.remove(suit)
            self.__removeStatus(suit, statusName=SuitStatusNames[2])

    def __clearTrapCreator(self, creatorId, suit=None):
        if not suit:
            for suit in self.trappedSuits:
                trapStatus = suit.getStatus(SuitStatusNames[2])
                if trapStatus['toon'] == creatorId:
                    trapStatus['toon'] = 0
            return
        trapStatus = suit.getStatus(SuitStatusNames[2])
        if trapStatus:
            trapStatus['toon'] = 0

    def __getSuitTrapType(self, suit):
        suitId = suit.getDoId()
        trapStatus = suit.getStatus(SuitStatusNames[2])
        if trapStatus:
            if suitId in self.trapCollisions:
                self.notify.info('%s used to have a trap, but it was removed.' % suitId)
                return NO_TRAP
            else:
                self.notify.info('%s is currently trapped!' % suitId)
                return trapStatus['level']
        else:
            self.notify.info('%s has no trap.' % suitId)
            return NO_TRAP

    # noinspection PyMethodMayBeStatic
    def __getTrapInfo(self, suit):
        if SuitStatusNames[2] in suit.statuses:
            trapStatus = suit.getStatus(SuitStatusNames[2])
            attackLevel = trapStatus['level']
            attackDamage = trapStatus['damage']
            trapCreatorId = trapStatus['toon']
        else:
            attackLevel = NO_TRAP
            attackDamage = 0
            trapCreatorId = 0
        return attackDamage, attackLevel, trapCreatorId

# LURE STATUS CALCULATION =============================================================================================

    def __lureSuit(self, atkLevel, attack, target, toonId):
        targetLured = 0
        validTargetAvail = 0
        if not target.getStatus(SuitStatusNames[0]):
            validTargetAvail = target.getHP() > 0
            if attack[TOON_TRACK_COL] == NPCSOS:
                self.__addLureStatus(target, atkLevel)
            else:
                self.__addLureStatus(target, atkLevel, toonId)
            targetLured = 1
        return targetLured, validTargetAvail

    def __addLureStatus(self, suit, atkLevel, toonId=-1):
        lureStatus = getSuitStatus(SuitStatusNames[0])
        rounds = self.NumRoundsLured[atkLevel]
        lureStatus['rounds'] = rounds
        lureStatus['toons'].append(toonId)
        lureStatus['levels'].append(atkLevel)
        if self.__getToonPrestige(toonId, LURE_TRACK):
            lureStatus['decay'] = 110
            lureStatus['kbBonus'] = 0.65
        suit.b_addStatus(lureStatus)
        self.notify.info('%s now has a level %d lure for %d rounds.' % (suit.doId, atkLevel, rounds))
        self.luredSuits.append(suit)

    def __addSuitToDelayedWake(self, toonId, target=None, ignoreDamageCheck=False):
        if not target:
            self.delayedWakes.append(target)
        else:
            targetList = self.__createToonTargetList(toonId)
            for thisTarget in targetList:
                attack = self.battle.toonAttacks[toonId]
                pos = self.battle.activeSuits.index(thisTarget)
                if (thisTarget.getStatus(SuitStatusNames[0]) and target not in self.delayedWakes and
                        (attack[TOON_HP_COL][pos] > 0 or ignoreDamageCheck)):
                    self.delayedWakes.append(target)

    def __wakeSuitFromAttack(self, toonId):
        targetList = self.__createToonTargetList(toonId)
        for target in targetList:
            luredStatus = target.getStatus(SuitStatusNames[0])
            if luredStatus and self.__bonusExists(target, hp=0):
                self.__removeLureStatus(target, luredStatus)
                self.notify.debug('Suit %d stepping from lured spot' % target.getDoId())
            else:
                self.notify.debug('Suit ' + str(target.doId) + ' not found in currently lured suits')

    def __wakeDelayedLures(self):
        for target in self.delayedWakes:
            if not target:
                continue
            luredStatus = target.getStatus(SuitStatusNames[0])
            if luredStatus:
                self.__removeLureStatus(target, luredStatus)
                self.notify.debug('Suit %d will be stepping back from lured spot' % target.doId)
            else:
                self.notify.debug('Suit ' + str(target.doId) + ' not found in currently lured suits')

        self.delayedWakes = []

    def __removeLureStatus(self, suit, statusRemoved=None):
        if suit in self.luredSuits:
            self.luredSuits.remove(suit)
            if statusRemoved:
                self.__removeStatus(suit, statusRemoved)
            else:
                self.__removeStatus(suit, statusName=SuitStatusNames[0])

    @staticmethod
    def __getLuredExpInfo(suit):
        returnInfo = []
        lureStatus = suit.getStatus(SuitStatusNames[0])
        lureToons = lureStatus['toons']
        lureLevels = lureStatus['levels']
        if len(lureToons) == 0:
            return returnInfo
        for i in xrange(len(lureToons)):
            if lureToons[i] != -1:
                returnInfo.append([lureToons[i], lureLevels[i]])

        return returnInfo

# SOAK STATUS CALCULATION =============================================================================================

    def __soakSuit(self, atkLevel, toon, target):
        soakStatus = target.getStatus(SuitStatusNames[1])
        soakRounds = self.NumRoundsSoaked[atkLevel]
        if not soakStatus or soakStatus['rounds'] < soakRounds:
            if soakStatus:
                self.__removeStatus(target, soakStatus)
            self.__addSoakStatus(target, soakRounds)

    def __addSoakStatus(self, suit, rounds):
        soakStatus = getSuitStatus(SuitStatusNames[1])
        soakStatus['rounds'] = rounds
        suit.b_addStatus(soakStatus)
        self.notify.info('%s now is soaked for %d rounds.' % (suit.doId, rounds))
        self.soakedSuits.append(suit)

    def __removeSoakStatus(self, suit, statusRemoved=None):
        if suit in self.soakedSuits:
            self.soakedSuits.remove(suit)
            self.soaksEnded.append(suit)
            if statusRemoved:
                self.__removeStatus(suit, statusRemoved)
            else:
                self.__removeStatus(suit, statusName=SuitStatusNames[0])

# MISC STATUS FUNCTIONS ===============================================================================================

    def __removeStatus(self, suit, status=None, statusName=''):
        if statusName:
            status = suit.getStatus(statusName)
        elif status:
            statusName = status['name']

        if statusName not in self.lostStatusesDict:
            self.lostStatusesDict[status['name']] = {}
        self.lostStatusesDict[status['name']][suit] = status
        suit.b_removeStatus(statusName)
        self.notify.info('%s just lost its %s status.' % (suit.doId, statusName))

# SUIT ATTACK SELECTION ===============================================================================================

    def __calculateSuitAttacks(self):
        suitAttacks = self.battle.suitAttacks
        for i in xrange(len(suitAttacks)):
            if i < len(self.battle.activeSuits):
                suit = self.battle.activeSuits[i]
                suitId = self.battle.activeSuits[i].doId
                suitAttacks[i][SUIT_ID_COL] = suitId
                if not self.__suitCanAttack(suit):
                    if self.notify.getDebug():
                        self.notify.debug("Suit %d can't attack" % suitId)
                    continue
                if self.battle.pendingSuits.count(self.battle.activeSuits[i]) > 0 or self.battle.joiningSuits.count(
                        self.battle.activeSuits[i]) > 0:
                    continue
                attack = suitAttacks[i]
                attack[SUIT_ID_COL] = self.battle.activeSuits[i].doId
                attack[SUIT_ATK_COL] = self.__calcSuitAtkType(i)
                attack[SUIT_TGT_COL] = self.__calcSuitTarget(i)
                if attack[SUIT_TGT_COL] == -1:
                    suitAttacks[i] = getDefaultSuitAttack()
                    attack = suitAttacks[i]
                    self.notify.debug('clearing suit attack, no avail targets')
                self.__calcSuitAtkHp(i)
                if attack[SUIT_ATK_COL] != NO_ATTACK:
                    if self.__suitAtkAffectsGroup(attack):
                        for currTgt in self.battle.activeToons:
                            self.__updateSuitAtkStat(currTgt)

                    else:
                        tgtId = self.battle.activeToons[attack[SUIT_TGT_COL]]
                        self.__updateSuitAtkStat(tgtId)
                targets = self.__createSuitTargetList(i)
                allTargetsDead = 1
                for currTgt in targets:
                    if self.__getToonHp(currTgt) > 0:
                        allTargetsDead = 0
                        break

                if allTargetsDead:
                    suitAttacks[i] = getDefaultSuitAttack()
                    if self.notify.getDebug():
                        self.notify.debug('clearing suit attack, targets dead')
                        self.notify.debug('suit attack is now ' + repr(suitAttacks[i]))
                        self.notify.debug('all attacks: ' + repr(suitAttacks))
                    attack = suitAttacks[i]
                if self.__attackHasHit(attack, suit=1):
                    self.__applySuitAttackDamages(i)
                if self.notify.getDebug():
                    self.notify.debug('Suit attack: ' + str(suitAttacks[i]))
                attack[SUIT_BEFORE_TOONS_COL] = 0

    def __calcSuitAtkType(self, attackIndex):
        theSuit = self.battle.activeSuits[attackIndex]
        attacks = SuitBattleGlobals.SuitAttributes[theSuit.dna.name]['attacks']
        atk = SuitBattleGlobals.pickSuitAttack(attacks, theSuit.getLevel())
        return atk

    def __calcSuitTarget(self, attackIndex):
        suitId = self.battle.suitAttacks[attackIndex][SUIT_ID_COL]
        if suitId in self.SuitAttackers and random.randint(0, 99) < 75:
            totalDamage = 0
            for currToon in self.SuitAttackers[suitId].keys():
                totalDamage += self.SuitAttackers[suitId][currToon]

            damages = []
            for currToon in self.SuitAttackers[suitId].keys():
                damages.append(self.SuitAttackers[suitId][currToon] / totalDamage * 100)

            dmgIdx = SuitBattleGlobals.pickFromFreqList(damages)
            if dmgIdx:
                toonId = self.__pickRandomToon(suitId)
            else:
                toonId = random.choice(self.SuitAttackers[suitId].keys())
            if toonId == -1 or toonId not in self.battle.activeToons:
                return -1
            self.notify.debug('Suit attacking back at toon ' + str(toonId))
            return self.battle.activeToons.index(toonId)
        else:
            return self.__pickRandomToon(suitId)

    def __pickRandomToon(self, suitId):
        liveToons = []
        for currToon in self.battle.activeToons:
            if not self.__getToonHp(currToon) <= 0:
                liveToons.append(self.battle.activeToons.index(currToon))

        if len(liveToons) == 0:
            self.notify.debug('No targets avail. for suit ' + str(suitId))
            return -1
        chosen = random.choice(liveToons)
        self.notify.debug('Suit randomly attacking toon ' + str(self.battle.activeToons[chosen]))
        return chosen

    def __calcSuitAtkHp(self, attackIndex):
        targetList = self.__createSuitTargetList(attackIndex)
        attack = self.battle.suitAttacks[attackIndex]
        for currTarget in xrange(len(targetList)):
            toonId = targetList[currTarget]
            toon = self.battle.getToon(toonId)
            result = 0
            if toon and toon.immortalMode:
                result = 1
            elif self.TOONS_TAKE_NO_DAMAGE:
                result = 0
            elif self.__suitAtkHit(attackIndex):
                atkType = attack[SUIT_ATK_COL]
                theSuit = self.battle.findSuit(attack[SUIT_ID_COL])
                atkInfo = SuitBattleGlobals.getSuitAttack(theSuit.dna.name, theSuit.getLevel(), atkType)
                result = int(atkInfo['hp'] +
                             math.ceil(atkInfo['hp'] * SuitBattleGlobals.EXE_DMG_MOD * theSuit.isExecutive))
            targetIndex = self.battle.activeToons.index(toonId)
            attack[SUIT_HP_COL][targetIndex] = result

    def __suitAtkHit(self, attackIndex):
        if self.suitsAlwaysHit:
            return 1
        else:
            if self.suitsAlwaysMiss:
                return 0
        theSuit = self.battle.activeSuits[attackIndex]
        atkType = self.battle.suitAttacks[attackIndex][SUIT_ATK_COL]
        atkInfo = SuitBattleGlobals.getSuitAttack(theSuit.dna.name, theSuit.getLevel(), atkType)
        atkAcc = atkInfo['acc']
        suitAcc = SuitBattleGlobals.SuitAttributes[theSuit.dna.name]['acc'][theSuit.getLevel()]
        acc = atkAcc
        randChoice = random.randint(0, 99)
        self.notify.debug('Suit attack rolled %s to hit with an accuracy of %s (attackAcc: %s suitAcc: %s)' %
                          (randChoice, acc, atkAcc, suitAcc))
        if randChoice < acc:
            return 1
        return 0

    def __suitAtkAffectsGroup(self, attack):
        atkType = attack[SUIT_ATK_COL]
        theSuit = self.battle.findSuit(attack[SUIT_ID_COL])
        atkInfo = getSuitAttack(theSuit.dna.name, theSuit.getLevel(), atkType)
        return atkInfo['group'] != ATK_TGT_SINGLE

    def __createSuitTargetList(self, attackIndex):
        attack = self.battle.suitAttacks[attackIndex]
        targetList = []
        if attack[SUIT_ATK_COL] == NO_ATTACK:
            self.notify.debug('No attack, no targets')
            return targetList
        if not self.__suitAtkAffectsGroup(attack):
            targetList.append(self.battle.activeToons[attack[SUIT_TGT_COL]])
            self.notify.debug('Suit attack is single target')
        else:
            self.notify.debug('Suit attack is group target')
            for currToon in self.battle.activeToons:
                self.notify.debug('Suit attack will target toon' + str(currToon))
                targetList.append(currToon)

        return targetList

    def __applySuitAttackDamages(self, attackIndex):
        attack = self.battle.suitAttacks[attackIndex]
        if self.APPLY_HEALTH_ADJUSTMENTS:
            for toon in self.battle.activeToons:
                position = self.battle.activeToons.index(toon)
                if attack[SUIT_HP_COL][position] <= 0:
                    continue
                toonHp = self.__getToonHp(toon)
                if toonHp - attack[SUIT_HP_COL][position] <= 0:
                    self.notify.debug('Toon %d has died, removing' % toon)
                    self.toonLeftBattle(toon)
                    attack[TOON_DIED_COL] = attack[TOON_DIED_COL] | 1 << position
                if self.notify.getDebug():
                    self.notify.debug('Toon %s takes %s damage' % (toon, attack[SUIT_HP_COL][position]))
                self.toonHPAdjusts[toon] -= attack[SUIT_HP_COL][position]
                self.notify.debug('Toon %s now has %s health' % (toon, self.__getToonHp(toon)))

    def __suitCanAttack(self, suit):
        defeated = not suit.getHP() > 0
        rounds = suit.getLureRounds()
        revived = suit.reviveCheckAndClear()
        self.notify.info('Can %s attack? Defeated: %s LureRounds: %s NewlyRevived: %s' %
                         (suit.doId, defeated, rounds, revived))
        if defeated or rounds >= 1 or revived:
            return 0
        return 1

    def __updateSuitAtkStat(self, toonId):
        if toonId in self.suitAtkStats:
            self.suitAtkStats[toonId] += 1
        else:
            self.suitAtkStats[toonId] = 1
    
# BATTLE ESCAPE FUNCTIONS =============================================================================================

    def toonLeftBattle(self, toonId):
        if self.notify.getDebug():
            self.notify.debug('toonLeftBattle()' + str(toonId))
        if toonId in self.toonSkillPtsGained:
            del self.toonSkillPtsGained[toonId]
        if toonId in self.suitAtkStats:
            del self.suitAtkStats[toonId]
        if not self.CLEAR_SUIT_ATTACKERS:
            oldSuitIds = []
            for s in self.SuitAttackers.keys():
                if toonId in self.SuitAttackers[s]:
                    del self.SuitAttackers[s][toonId]
                    if len(self.SuitAttackers[s]) == 0:
                        oldSuitIds.append(s)

            for oldSuitId in oldSuitIds:
                del self.SuitAttackers[oldSuitId]

        self.__clearTrapCreator(toonId)

    def suitLeftBattle(self, suit):
        suitId = suit.getDoId()
        self.notify.debug('suitLeftBattle(): ' + str(suitId))
        self.__removeLureStatus(suit)
        self.__removeTrapStatus(suit)
        if suitId in self.SuitAttackers:
            del self.SuitAttackers[suitId]
    
# VARIOUS PROPERTY GETTERS ============================================================================================

    def __getToonHp(self, toonDoId):
        handle = self.battle.getToon(toonDoId)
        if handle and toonDoId in self.toonHPAdjusts:
            return handle.hp + self.toonHPAdjusts[toonDoId]
        else:
            return 0

    def __getToonMaxHp(self, toonDoId):
        handle = self.battle.getToon(toonDoId)
        if handle:
            return handle.maxHp
        else:
            return 0

    def __prevAtkTrack(self, attackerId, toon=1):
        if toon:
            prevAtkIdx = self.toonAtkOrder.index(attackerId) - 1
            if prevAtkIdx >= 0:
                prevAttackerId = self.toonAtkOrder[prevAtkIdx]
                attack = self.battle.toonAttacks[prevAttackerId]
                return self.__getActualTrack(attack)
            else:
                return NO_ATTACK

    def __attackHasHit(self, attack, suit=0):
        if suit:
            for dmg in attack[SUIT_HP_COL]:
                if dmg > 0:
                    return 1
            return 0
        else:
            track = self.__getActualTrack(attack)
            return not attack[TOON_ACCBONUS_COL] and track != NO_ATTACK

    def __getActualTrack(self, toonAttack):
        if toonAttack[TOON_TRACK_COL] == NPCSOS:
            track = NPCToons.getNPCTrack(toonAttack[TOON_TGT_COL])
            if track is not None:
                return track
            else:
                self.notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
        return toonAttack[TOON_TRACK_COL]

    def __getActualTrackLevel(self, toonAttack):
        if toonAttack[TOON_TRACK_COL] == NPCSOS:
            track, level, hp = NPCToons.getNPCTrackLevelHp(toonAttack[TOON_TGT_COL])
            if track is not None:
                return track, level
            else:
                self.notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
        return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL]

    def __getActualTrackLevelHp(self, toonAttack):
        if toonAttack[TOON_TRACK_COL] == NPCSOS:
            track, level, hp = NPCToons.getNPCTrackLevelHp(toonAttack[TOON_TGT_COL])
            if track:
                return track, level, hp
            else:
                self.notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
        else:
            if toonAttack[TOON_TRACK_COL] == PETSOS:
                petProxyId = toonAttack[TOON_TGT_COL]
                trickId = toonAttack[TOON_LVL_COL]
                healRange = PetTricks.TrickHeals[trickId]
                hp = 0
                if petProxyId in simbase.air.doId2do:
                    petProxy = simbase.air.doId2do[petProxyId]
                    if trickId < len(petProxy.trickAptitudes):
                        aptitude = petProxy.trickAptitudes[trickId]
                        hp = int(lerp(healRange[0], healRange[1], aptitude))
                else:
                    self.notify.warning('pet proxy: %d not in doId2do!' % petProxyId)
                return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL], hp
        return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL], 0

    def __calculatePetTrickSuccess(self, toonAttack):
        petProxyId = toonAttack[TOON_TGT_COL]
        if petProxyId not in simbase.air.doId2do:
            self.notify.warning('pet proxy %d not in doId2do!' % petProxyId)
            toonAttack[TOON_ACCBONUS_COL] = 1
            return 0
        petProxy = simbase.air.doId2do[petProxyId]
        trickId = toonAttack[TOON_LVL_COL]
        toonAttack[TOON_ACCBONUS_COL] = petProxy.attemptBattleTrick(trickId)
        if toonAttack[TOON_ACCBONUS_COL] == 1:
            return 0
        else:
            return 1
