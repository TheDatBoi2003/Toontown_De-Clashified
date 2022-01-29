from DistributedBattleAI import *
from toontown.battle import BattleExperienceAI
from toontown.battle.calc import BattleCalculatorGlobals
from toontown.battle.calc.HealCalculatorAI import *
from toontown.battle.calc.LureCalculatorAI import *
from toontown.battle.calc.SquirtCalculatorAI import *
from toontown.battle.calc.TrapCalculatorAI import *
from toontown.battle.calc.ZapCalculatorAI import *
from toontown.toonbase.ToontownBattleGlobals import RAILROAD_LEVEL_INDEX


class BattleCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('BattleCalculatorAI')
    notify.setDebug(True)
    toonsAlwaysHit = simbase.config.GetBool('toons-always-hit', 0)
    toonsAlwaysMiss = simbase.config.GetBool('toons-always-miss', 0)
    toonsAlways5050 = simbase.config.GetBool('toons-always-5050', 0)
    suitsAlwaysHit = simbase.config.GetBool('suits-always-hit', 0)
    suitsAlwaysMiss = simbase.config.GetBool('suits-always-miss', 0)
    immortalSuits = simbase.config.GetBool('immortal-suits', 0)

    # INIT and CLEANUP: Class constructor and destructor ===============================================================
    # ==================================================================================================================

    def __init__(self, battle, tutorialFlag=0):
        DirectObject.__init__(self)
        self.battle = battle
        self.SuitAttackers = {}
        self.statusCalculator = StatusCalculatorAI(self.battle)
        self.healCalculator = HealCalculatorAI(self.battle, self.statusCalculator)
        self.trapCalculator = TrapCalculatorAI(self.battle, self.statusCalculator)
        self.lureCalculator = LureCalculatorAI(self.battle, self.statusCalculator, self.trapCalculator)
        self.squirtCalculator = SquirtCalculatorAI(self.battle, self.statusCalculator)
        self.zapCalculator = ZapCalculatorAI(self.battle, self.squirtCalculator)
        self.trackCalculators = {HEAL: self.healCalculator,
                                 TRAP: self.trapCalculator,
                                 LURE: self.lureCalculator,
                                 SQUIRT: self.squirtCalculator,
                                 ZAP: self.zapCalculator}
        self.toonAtkOrder = []
        self.toonSkillPtsGained = {}
        self.suitAtkStats = {}
        self.__clearBonuses()
        self.__skillCreditMultiplier = 1
        self.tutorialFlag = tutorialFlag
        self.accept('add-exp', self.__addAttackExp)
        self.accept('suit-hit', self.__rememberToonAttack)

    def cleanup(self):
        for trackCalculator in self.trackCalculators.values():
            if trackCalculator:
                trackCalculator.cleanup()
                del trackCalculator
        self.battle = None
        return

    # PUBLIC ACCESS FUNCTIONS ==========================================================================================
    # ==================================================================================================================

    def setSkillCreditMultiplier(self, mult):
        self.__skillCreditMultiplier = mult

    def getSkillGained(self, toonId, track):
        return BattleExperienceAI.getSkillGained(self.toonSkillPtsGained, toonId, track)

    def getLuredSuits(self):
        luredSuits = self.lureCalculator.luredSuits
        self.notify.debug('Lured suits reported to battle: ' + repr(luredSuits))
        return luredSuits

    def addTrainTrapForJoiningSuit(self, suitId):
        trapInfoToUse = None
        for suit in self.trapCalculator.trappedSuits:
            trapStatus = suit.getStatus(SuitStatusNames[2])
            if trapStatus and trapStatus['level'] == RAILROAD_LEVEL_INDEX:
                trapInfoToUse = trapStatus
                break

        if trapInfoToUse:
            self.battle.findSuit(suitId).b_addStatus(trapInfoToUse)
        else:
            self.notify.warning('There is no train trap on %s for some reason!' % suitId)
        return

    # BEGIN ROUND CALCULATIONS =========================================================================================
    # ==================================================================================================================

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
                return

        self.__calculateToonAttacks()
        messenger.send('post-toon')
        self.__calculateSuitAttacks()
        messenger.send('post-suit')
        messenger.send('round-over')
        return

    def __initRound(self):
        if CLEAR_SUIT_ATTACKERS:
            self.SuitAttackers = {}
        self.__findToonAttacks()

        self.notify.debug('Toon attack order: ' + str(self.toonAtkOrder))
        self.notify.debug('Active toons: ' + str(self.battle.activeToons))
        self.notify.debug('Toon attacks: ' + str(self.battle.toonAttacks))
        self.notify.debug('Active suits: ' + str(self.battle.activeSuits))
        self.notify.debug('Suit attacks: ' + str(self.battle.suitAttacks))

        self.__clearBonuses()
        self.__updateActiveToons()
        messenger.send('init-round')
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

        self.creditLevel = getHighestTargetLevel(self.battle)
        for toonId in self.toonAtkOrder:
            if self.healCalculator.getToonHp(toonId) <= 0:
                self.notify.debug("Toon %d is dead and can't attack" % toonId)
                continue
            attack = self.battle.toonAttacks[toonId]
            atkTrack = getActualTrack(attack, self.notify)
            if atkTrack not in [NO_ATTACK, SOS, NPCSOS]:
                self.notify.debug('Calculating attack for toon: %d' % toonId)
                isFirstOfCurrentTrack = not currTrack or atkTrack == currTrack
                if SUITS_WAKE_IMMEDIATELY and not isFirstOfCurrentTrack:
                    self.lureCalculator.wakeDelayedLures()
                currTrack = atkTrack
                self.__calcToonAttackHp(toonId)
                attackIdx = self.toonAtkOrder.index(toonId)
                self.__handleBonus(attackIdx)
                lastAttack = attackIdx >= len(self.toonAtkOrder) - 1
                if attackHasHit(attack, self.notify, suit=0) and atkTrack in [THROW, SQUIRT, DROP]:
                    if lastAttack:
                        self.lureCalculator.wakeSuitFromAttack(self, toonId)
                    else:
                        messenger.send('delayed-wake', [toonId])
                if lastAttack:
                    self.lureCalculator.wakeDelayedLures()

        messenger.send('pre-bonuses', [self.toonAtkOrder])
        self.__processBonuses(self.hpBonuses)
        self.notify.debug('Processing hpBonuses: ' + repr(self.hpBonuses))
        self.__processBonuses(self.kbBonuses)
        self.notify.debug('Processing kbBonuses: ' + repr(self.kbBonuses))
        self.__postProcessToonAttacks()
        return

    def __updateActiveToons(self):
        self.notify.debug('updateActiveToons()')

        if not CLEAR_SUIT_ATTACKERS:
            oldSuitIds = []
            for s in self.SuitAttackers.keys():
                for t in self.SuitAttackers[s].keys():
                    if t not in self.battle.activeToons:
                        del self.SuitAttackers[s][t]
                        if len(self.SuitAttackers[s]) == 0:
                            oldSuitIds.append(s)

            for oldSuitId in oldSuitIds:
                del self.SuitAttackers[oldSuitId]

        messenger.send('update-active-toons')

        for suit in self.trapCalculator.trappedSuits:
            trapStatus = suit.getStatus(SuitStatusNames[2])
            if trapStatus['toon'] not in self.battle.activeToons:
                self.notify.debug('Trap for toon ' + str(trapStatus['toon']) + ' will no longer give exp')
                trapStatus['toon'] = 0

    # TOON ACCURACY CALCULATION ========================================================================================

    def __calcToonAttackHit(self, attackIndex, atkTargets):
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
        if self.toonsAlwaysMiss:
            return 0

        attackId = self.battle.toonAttacks[attackIndex]
        atkTrack, atkLevel = getActualTrackLevel(attackId, self.notify)
        if atkTrack == NPCSOS or atkTrack == FIRE:
            return 1
        if atkTrack == TRAP:
            attackId[TOON_MISSED_COL] = 0
            return 1
        if atkTrack == PETSOS:
            return calculatePetTrickSuccess(attackId, self.notify)
        if atkTrack == ZAP:
            currAtk = self.toonAtkOrder.index(attackIndex)
            prevAtkTrack, prevAttack = self.__getPreviousAttack(currAtk)
            attackId[TOON_MISSED_COL] = self.zapCalculator.calcZapHit(attackIndex, atkTargets[0],
                                                                    currAtk, prevAttack, prevAtkTrack)
            return not attackId[TOON_MISSED_COL]

        tgtDef = 0
        highestDecay = 0
        if atkTrack not in HEALING_TRACKS:
            highestDecay, tgtDef = findLowestDefense(atkTargets, tgtDef, self.notify)

        trackExp = self.__checkTrackAccBonus(attackId[TOON_ID_COL], atkTrack)
        trackExp = self.__findHighestTrackBonus(atkTrack, attackId, trackExp)

        propAcc = AvPropAccuracy[atkTrack][atkLevel]

        currAtk = self.toonAtkOrder.index(attackIndex)
        if atkTrack == DROP and currAtk == 0:
            singleDrop = 1
            for attackId in self.toonAtkOrder:
                if attackId in self.battle.toonAttacks and self.battle.toonAttacks[attackId][TOON_TRACK_COL] == DROP:
                    singleDrop = 0
                    break
            if singleDrop:
                prestige = getToonPrestige(self.battle, attackId[TOON_ID_COL], atkTrack)
                propBonus = getToonPropBonus(self.battle, atkTrack)
                if PropAndPrestigeStack:
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

        if currAtk > 0 and atkTrack != HEAL:
            prevAtkTrack, prevAttack = self.__getPreviousAttack(currAtk)
            if (atkTrack == prevAtkTrack and (attackId[TOON_TGT_COL] == prevAttack[TOON_TGT_COL]
                                              or atkTrack == LURE
                                              and (not attackAffectsGroup(atkTrack, atkLevel, attackId[TOON_TRACK_COL])
                                                   and attackId[TOON_TGT_COL] in self.lureCalculator.successfulLures
                                                   or attackAffectsGroup(atkTrack, atkLevel, attackId[TOON_TRACK_COL])))):
                if prevAttack[TOON_MISSED_COL]:
                    self.notify.debug('DODGE: Toon attack track dodged')
                else:
                    self.notify.debug('HIT: Toon attack track hit')
                attackId[TOON_MISSED_COL] = prevAttack[TOON_MISSED_COL]
                return not attackId[TOON_MISSED_COL]

        acc = attackAcc + self.__calcPrevAttackBonus(attackIndex)

        if atkTrack != LURE and atkTrack not in HEALING_TRACKS:
            acc = max(acc, highestDecay)

        if acc > MaxToonAcc and highestDecay < 100:
            acc = MaxToonAcc

        self.notify.debug('setting accuracy result to %d' % acc)

        if attackId[TOON_TRACK_COL] == NPCSOS:
            randChoice = 0
        else:
            randChoice = random.randint(0, 99)
        if randChoice < acc:
            self.notify.debug('HIT: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            attackId[TOON_MISSED_COL] = 0
        else:
            self.notify.debug('MISS: Toon attack rolled' + str(randChoice) + 'to hit with an accuracy of' + str(acc))
            attackId[TOON_MISSED_COL] = 1
        return not attackId[TOON_MISSED_COL]

    def __calcPrevAttackBonus(self, attackKey):
        numPrevHits = 0
        attackIdx = self.toonAtkOrder.index(attackKey)
        for currPrevAtk in xrange(attackIdx - 1, -1, -1):
            attack = self.battle.toonAttacks[attackKey]
            atkTrack, atkLevel = getActualTrackLevel(attack, self.notify)
            prevAttackKey = self.toonAtkOrder[currPrevAtk]
            prevAttack = self.battle.toonAttacks[prevAttackKey]
            prvAtkTrack, prvAtkLevel = getActualTrackLevel(prevAttack, self.notify)
            if (attackHasHit(prevAttack, self.notify)
                    and (attackAffectsGroup(prvAtkTrack, prvAtkLevel, prevAttack[TOON_TRACK_COL])
                         or attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL])
                         or attack[TOON_TGT_COL] == prevAttack[TOON_TGT_COL])
                    and atkTrack != prvAtkTrack):
                numPrevHits += 1

        if numPrevHits > 0:
            self.notify.debug('ACC BONUS: toon attack received accuracy bonus of ' +
                              str(BattleCalculatorGlobals.AccuracyBonuses[numPrevHits]) + ' from previous attack')
        return BattleCalculatorGlobals.AccuracyBonuses[numPrevHits]

    def __findHighestTrackBonus(self, atkTrack, attack, trackExp):
        for currOtherAtk in self.toonAtkOrder:
            if currOtherAtk != attack[TOON_ID_COL]:
                nextAttack = self.battle.toonAttacks[currOtherAtk]
                nextAtkTrack = getActualTrack(nextAttack, self.notify)
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
            exp = AttackExpPerTrack[toonExpLvl]
            if track == HEAL:
                exp = exp * 0.5
            self.notify.debug('Toon track exp: ' + str(toonExpLvl) + ' and resulting acc bonus: ' + str(exp))
            return exp
        else:
            return 0

    def __getPreviousAttack(self, currAtk):
        prevAtkId = self.toonAtkOrder[currAtk - 1]
        prevAttack = self.battle.toonAttacks[prevAtkId]
        prevAtkTrack = getActualTrack(prevAttack, self.notify)
        return prevAtkTrack, prevAttack

    # TOON DAMAGE/SUCCESS CALCULATION ==================================================================================

    def __calcToonAttackHp(self, toonId):
        attack = self.battle.toonAttacks[toonId]
        targetList = createToonTargetList(self.battle, toonId)
        atkHit = self.__calcToonAttackHit(toonId, targetList)
        atkTrack = getActualTrack(attack, self.notify)
        if not atkHit and atkTrack != HEAL:
            return

        if atkTrack in HEALING_TRACKS:
            targets = self.battle.activeToons
        else:
            targets = self.battle.activeSuits

        if atkTrack in self.trackCalculators:
            targetsExist = self.trackCalculators[atkTrack].calcAttackResults(attack, targets, toonId)
        else:
            targetsExist = self.calcAttackResults(attack, targets, toonId)

        if not targetsExist and self.__prevAtkTrack(toonId) != atkTrack:
            self.notify.debug('Something happened to our target!  Removing attack...')
            self.__clearAttack(toonId)
        return

    def calcAttackResults(self, attack, targets, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack, self.notify)
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        results = [0 for _ in xrange(len(targets))]
        targetsExist = 0
        for target in targetList:
            npcSOS = atkTrack == NPCSOS
            kbBonuses = attack[TOON_KBBONUS_COL]
            if atkTrack == PETSOS:
                result = atkHp
                targetsExist += self.healCalculator.getToonHp(target) > 0
            elif atkTrack == FIRE:
                result = 0
                if target:
                    costToFire = 1
                    abilityToFire = toon.getPinkSlips()
                    toon.removePinkSlips(costToFire)
                    if costToFire <= abilityToFire:
                        target.skeleRevives = 0
                        result = target.getHP()
                result = result
                targetsExist += target.getHP() > 0
            elif atkTrack == SOUND:
                if target.getStatus(LURED_STATUS):
                    self.notify.debug('Sound on lured suit, ' + 'indicating with KB_BONUS_COL flag')
                    pos = self.battle.activeSuits.index(target)
                    kbBonuses[pos] = KB_BONUS_LURED_FLAG
                    messenger.send('delayed-wake', [toonId, target])
                result = doInstaKillCalc(self.battle, atkHp, atkLevel, atkTrack, npcSOS, target, toon,
                                         PropAndPrestigeStack)
                targetsExist += target.getHP() > 0
            elif atkTrack == DROP:
                if target.getStatus(LURED_STATUS):
                    result, targetExists = 0, 0
                    self.notify.debug('setting damage to 0, since drop on a lured suit')
                else:
                    result = doInstaKillCalc(self.battle, atkHp, atkLevel, atkTrack, npcSOS, target, toon,
                                             PropAndPrestigeStack)
                targetsExist += target.getHP() > 0
            else:
                result = doInstaKillCalc(self.battle, atkHp, atkLevel, atkTrack, npcSOS, target, toon,
                                         PropAndPrestigeStack)
                targetsExist += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, result))

            if result != 0:
                if target not in targets:
                    self.notify.debug("The target is not accessible!")
                    continue

                if result > 0 and target in self.lureCalculator.luredSuits:
                    messenger.send('lured-hit-exp', [attack, target])

                results[targets.index(target)] = result
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsExist

    def __clearAttack(self, attackIdx):
        self.notify.debug('clearing out toon attack for toon ' + str(attackIdx) + '...')
        self.battle.toonAttacks[attackIdx] = getToonAttack(attackIdx)
        longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
        for j in xrange(longest):
            self.battle.toonAttacks[attackIdx][TOON_HP_COL].append(-1)
            self.battle.toonAttacks[attackIdx][TOON_HPBONUS_COL].append(-1)
            self.battle.toonAttacks[attackIdx][TOON_KBBONUS_COL].append(-1)

        if self.notify.getDebug():
            self.notify.debug('toon attack is now ' + repr(self.battle.toonAttacks[attackIdx]))

    def __postProcessToonAttacks(self):
        self.notify.debug('__postProcessToonAttacks()')
        lastTrack = -1
        lastAttacks = []
        self.__clearHpBonuses()
        for currentToon in self.toonAtkOrder:
            if currentToon != -1:
                self.__applyAttack(currentToon, lastAttacks, lastTrack)

        if self.trapCalculator.trainTrapTriggered:
            for suit in self.battle.activeSuits:
                suitId = suit.doId
                self.trapCalculator.removeTrapStatus(suit)
                suit.battleTrap = NO_TRAP
                self.notify.debug('train trap triggered, removing trap from %d' % suitId)

        if self.notify.getDebug():
            for currentToon in self.toonAtkOrder:
                attack = self.battle.toonAttacks[currentToon]
                self.notify.debug('Final Toon attack: ' + str(attack))

    def __applyAttack(self, currentToon, lastAttacks, lastTrack):
        attack = self.battle.toonAttacks[currentToon]
        atkTrack, atkLevel = getActualTrackLevel(attack, self.notify)
        if atkTrack not in [HEAL, NO_ATTACK] + SOS_TRACKS:
            targets = createToonTargetList(self.battle, currentToon)
            allTargetsDead = 1
            for suit in targets:
                damageDone = getAttackDamage(attack)
                if damageDone > 0:
                    self.__rememberToonAttack(suit.getDoId(), attack[TOON_ID_COL], damageDone)
                if atkTrack == TRAP:
                    if suit in self.trapCalculator.trappedSuits:
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
                if tgtId in self.lureCalculator.successfulLures and atkTrack == LURE:
                    lureInfo = self.lureCalculator.successfulLures[tgtId]
                    self.notify.debug('applying lure data: ' + repr(lureInfo))
                    tgtPos = self.battle.activeSuits.index(suit)
                    if suit in self.trapCalculator.trappedSuits:
                        trapInfo = suit.getStatus(SuitStatusNames[2])
                        if trapInfo['level'] == RAILROAD_LEVEL_INDEX:
                            self.notify.debug('train trap triggered for %d' % suit.doId)
                            self.trapCalculator.trainTrapTriggered = True
                        self.trapCalculator.removeTrapStatus(suit)
                    attack[TOON_KBBONUS_COL][tgtPos] = KB_BONUS_TGT_LURED
                    attack[TOON_HP_COL][tgtPos] = lureInfo[2]
                elif suit.getStatus(LURED_STATUS) and atkTrack == DROP:
                    tgtPos = self.battle.activeSuits.index(suit)
                    attack[TOON_KBBONUS_COL][tgtPos] = KB_BONUS_LURED_FLAG
                if targetDead and atkTrack != lastTrack:
                    tgtPos = self.battle.activeSuits.index(suit)
                    attack[TOON_HP_COL][tgtPos] = 0
                    attack[TOON_KBBONUS_COL][tgtPos] = -1

            if allTargetsDead and atkTrack != lastTrack:
                if self.notify.getDebug():
                    self.notify.debug('all targets of toon attack ' + str(currentToon) + ' are dead')
                self.__clearAttack(currentToon)
                attack = self.battle.toonAttacks[currentToon]
                atkTrack, atkLevel = getActualTrackLevel(attack, self.notify)
        damagesDone = self.__applyToonAttackDamages(currentToon)
        if atkTrack not in [LURE, ZAP]:
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
            elif atkTrack == HEAL and damagesDone != 0:
                self.__addAttackExp(attack)
            else:
                self.__addAttackExp(attack)

    def __rememberToonAttack(self, suitId, toonId, damage):
        if suitId not in self.SuitAttackers:
            self.SuitAttackers[suitId] = {toonId: damage}
        else:
            if toonId not in self.SuitAttackers[suitId]:
                self.SuitAttackers[suitId][toonId] = damage
            else:
                if self.SuitAttackers[suitId][toonId] <= damage:
                    self.SuitAttackers[suitId] = [toonId, damage]

    def __applyToonAttackDamages(self, toonId, hpBonus=0, kbBonus=0):
        totalDamages = 0
        if not APPLY_HEALTH_ADJUSTMENTS:
            return totalDamages
        attack = self.battle.toonAttacks[toonId]
        track = getActualTrack(attack, self.notify)
        if track not in [NO_ATTACK, SOS, TRAP, NPCSOS]:
            if track in BattleCalculatorGlobals.HEALING_TRACKS:
                targets = self.battle.activeToons
            else:
                targets = self.battle.activeSuits
            for position in xrange(len(targets)):
                targetList = createToonTargetList(self.battle, toonId)
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
                if track in BattleCalculatorGlobals.HEALING_TRACKS:
                    totalDamages += self.healCalculator.healToon(target, attack, damageDone, position)
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
                        self.notify.debug('Suit ' + str(targetId) + ' bravely expired in combat')

        return totalDamages

    # TOON DAMAGE BONUS CALCULATION ====================================================================================

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
        atkDmg = getAttackDamage(attack)
        atkTrack = getActualTrack(attack, self.notify)
        if atkTrack not in [LURE, ZAP] or atkDmg > 0:
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

                    if hpBonus:
                        if attack[TOON_TRACK_COL] != ZAP and targetPos < len(attack[TOON_HPBONUS_COL]):
                            if attack[TOON_TRACK_COL] == DROP:
                                numOrgs = 0
                                for toonId in self.battle.activeToons:
                                    if self.battle.getToon(toonId).checkTrackPrestige(DROP):
                                        numOrgs += 1

                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (BattleCalculatorGlobals.DropDamageBonuses[numOrgs][
                                                        attackCount - 1] * 0.01))
                            else:
                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (BattleCalculatorGlobals.DamageBonuses[attackCount - 1] * 0.01))
                            self.notify.debug('Applying hp bonus to track ' +
                                              str(attack[TOON_TRACK_COL]) + ' of ' +
                                              str(attack[TOON_HPBONUS_COL][targetPos]))
                    elif len(attack[TOON_KBBONUS_COL]) > targetPos:
                        kbBonus = 0.5
                        unluredSuitDict = self.statusCalculator.getLostStatuses(LURED_STATUS)
                        unluredSuit = next((suit for suit in unluredSuitDict.keys()
                                            if self.battle.activeSuits[targetPos] == suit), None)
                        if unluredSuit:
                            kbBonus = unluredSuitDict[unluredSuit]['kbBonus']
                        attack[TOON_KBBONUS_COL][targetPos] = math.ceil(totalDamages * kbBonus)
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
        atkTrack = getActualTrack(attack, self.notify)
        if atkTrack == HEAL or atkTrack == PETSOS:
            return
        targets = createToonTargetList(self.battle, toonId)
        for currTgt in targets:
            tgtPos = self.battle.suits.index(currTgt)
            dmg = attack[TOON_HP_COL][tgtPos]
            if hp:
                self.__addBonus(attackIndex, self.hpBonuses[tgtPos], dmg, atkTrack)
                self.notify.debug(self.hpBonuses)
            elif currTgt.getStatus(LURED_STATUS):
                self.__addBonus(attackIndex, self.kbBonuses[tgtPos], dmg, atkTrack)

    @staticmethod
    def __addBonus(attackIndex, bonusTarget, dmg, track):
        if track in bonusTarget:
            bonusTarget[track].append((attackIndex, dmg))
        else:
            bonusTarget[track] = [(attackIndex, dmg)]

    def bonusExists(self, tgtSuit, hp=1):
        tgtPos = self.battle.activeSuits.index(tgtSuit)
        if hp:
            bonusLen = len(self.hpBonuses[tgtPos])
        else:
            bonusLen = len(self.kbBonuses[tgtPos])
        if bonusLen > 0:
            return 1
        return 0

    # TARGETING CALCULATION ===========================================================================================

    def __clearTgtDied(self, tgt, lastAtk, currAtk):
        position = self.battle.activeSuits.index(tgt)
        currAtkTrack = getActualTrack(currAtk, self.notify)
        lastAtkTrack = getActualTrack(lastAtk, self.notify)
        if currAtkTrack == lastAtkTrack and lastAtk[SUIT_DIED_COL] & 1 << position and \
                attackHasHit(currAtk, self.notify, suit=0):
            self.notify.debug('Clearing suit died for ' + str(tgt.getDoId()) + ' at position ' + str(
                    position) + ' from toon attack ' + str(lastAtk[TOON_ID_COL]) + ' and setting it for ' + str(
                    currAtk[TOON_ID_COL]))
            lastAtk[SUIT_DIED_COL] = lastAtk[SUIT_DIED_COL] ^ 1 << position
            self.suitLeftBattle(tgt)
            currAtk[SUIT_DIED_COL] = currAtk[SUIT_DIED_COL] | 1 << position

    def __allTargetsDead(self, attackIdx, toon=1):
        allTargetsDead = 1
        if toon:
            targets = createToonTargetList(self.battle, attackIdx)
            for currTgt in targets:
                if currTgt.getHp() > 0:
                    allTargetsDead = 0
                    break

        else:
            self.notify.warning('__allTargetsDead: suit ver. not implemented!')
        return allTargetsDead

    # EXPERIENCE CALCULATION ===========================================================================================

    def __addAttackExp(self, attack, attackTrack=-1, attackLevel=-1, attackerId=-1):
        track = -1
        level = -1
        toonId = -1
        if attackTrack != -1 and attackLevel != -1 and attackerId != -1:
            track = attackTrack
            level = attackLevel
            toonId = attackerId
        elif attackHasHit(attack, self.notify):
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
            self.notify.debug('%s gained %d %s EXP, current exp: %d' %
                              (toonId, (level + 1) * self.__skillCreditMultiplier, Tracks[track], expList[track]))
        return

    # SUIT ATTACK SELECTION ============================================================================================

    def __calculateSuitAttacks(self):
        suitAttacks = self.battle.suitAttacks
        for i in xrange(len(suitAttacks)):
            if i < len(self.battle.activeSuits):
                suit = self.battle.activeSuits[i]
                suitId = self.battle.activeSuits[i].doId
                suitAttacks[i][SUIT_ID_COL] = suitId
                if not self.__suitCanAttack(suit):
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
                    if self.healCalculator.getToonHp(currTgt) > 0:
                        allTargetsDead = 0
                        break

                if allTargetsDead:
                    suitAttacks[i] = getDefaultSuitAttack()
                    if self.notify.getDebug():
                        self.notify.debug('clearing suit attack, targets dead')
                        self.notify.debug('suit attack is now ' + repr(suitAttacks[i]))
                        self.notify.debug('all attacks: ' + repr(suitAttacks))
                    attack = suitAttacks[i]
                if attackHasHit(attack, self.notify, suit=1):
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
            if not self.healCalculator.getToonHp(currToon) <= 0:
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
            elif TOONS_TAKE_NO_DAMAGE:
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
        if APPLY_HEALTH_ADJUSTMENTS:
            for toon in self.battle.activeToons:
                self.healCalculator.hurtToon(attack, toon)

    def __suitCanAttack(self, suit):
        defeated = not suit.getHP() > 0
        rounds = self.lureCalculator.getLureRounds(suit)
        revived = suit.reviveCheckAndClear()
        self.notify.debug('Can %s attack? Defeated: %s LureRounds: %s NewlyRevived: %s' %
                          (suit.doId, defeated, rounds, revived))
        if defeated or rounds >= 1 or revived:
            return 0
        return 1

    def __updateSuitAtkStat(self, toonId):
        if toonId in self.suitAtkStats:
            self.suitAtkStats[toonId] += 1
        else:
            self.suitAtkStats[toonId] = 1

    # BATTLE ESCAPE FUNCTIONS ==========================================================================================

    def toonLeftBattle(self, toonId):
        self.notify.debug('toonLeftBattle()' + str(toonId))
        if toonId in self.toonSkillPtsGained:
            del self.toonSkillPtsGained[toonId]
        if toonId in self.suitAtkStats:
            del self.suitAtkStats[toonId]
        if not CLEAR_SUIT_ATTACKERS:
            oldSuitIds = []
            for s in self.SuitAttackers.keys():
                if toonId in self.SuitAttackers[s]:
                    del self.SuitAttackers[s][toonId]
                    if len(self.SuitAttackers[s]) == 0:
                        oldSuitIds.append(s)

            for oldSuitId in oldSuitIds:
                del self.SuitAttackers[oldSuitId]

        self.trapCalculator.clearTrapCreator(toonId)

    def suitLeftBattle(self, suit):
        suitId = suit.getDoId()
        self.notify.info('suitLeftBattle(): ' + str(suitId))
        self.lureCalculator.removeLureStatus(suit)
        self.trapCalculator.removeTrapStatus(suit)
        self.squirtCalculator.removeSoakStatus(suit)
        if suitId in self.SuitAttackers:
            del self.SuitAttackers[suitId]

    # VARIOUS PROPERTY GETTERS =========================================================================================

    def __prevAtkTrack(self, attackerId, toon=1):
        if toon:
            prevAtkIdx = self.toonAtkOrder.index(attackerId) - 1
            if prevAtkIdx >= 0:
                prevAttackerId = self.toonAtkOrder[prevAtkIdx]
                attack = self.battle.toonAttacks[prevAttackerId]
                return getActualTrack(attack, self.notify)
            else:
                return NO_ATTACK
