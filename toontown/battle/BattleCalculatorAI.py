import importlib

import toontown.battle.SuitBattleGlobals
from DistributedBattleAI import *
from toontown.battle import BattleExperienceAI
from toontown.battle.calc import BattleCalculatorGlobals as BCG
from toontown.battle.calc.DropCalculatorAI import *
from toontown.battle.calc.HealCalculatorAI import *
from toontown.battle.calc.LureCalculatorAI import *
from toontown.battle.calc.SoundCalculatorAI import *
from toontown.battle.calc.SquirtCalculatorAI import *
from toontown.battle.calc import SuitCalculatorAI as DefaultSuitCalculatorAI
from toontown.battle.calc.SuitCalculatorAI import *
from toontown.battle.calc.ThrowCalculatorAI import *
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
        self.statusCalculator = StatusCalculatorAI(self.battle)
        self.healCalculator = HealCalculatorAI(self.battle, self.statusCalculator)
        self.trapCalculator = TrapCalculatorAI(self.battle, self.statusCalculator)
        self.lureCalculator = LureCalculatorAI(self.battle, self.statusCalculator, self.trapCalculator)
        self.soundCalculator = SoundCalculatorAI(self.battle)
        self.squirtCalculator = SquirtCalculatorAI(self.battle, self.statusCalculator)
        self.zapCalculator = ZapCalculatorAI(self.battle, self.squirtCalculator)
        self.throwCalculator = ThrowCalculatorAI(self.battle, self.statusCalculator)
        self.dropCalculator = DropCalculatorAI(self.battle)
        self.trackCalculators = {HEAL: self.healCalculator,
                                 TRAP: self.trapCalculator,
                                 LURE: self.lureCalculator,
                                 SOUND: self.soundCalculator,
                                 SQUIRT: self.squirtCalculator,
                                 ZAP: self.zapCalculator,
                                 THROW: self.throwCalculator,
                                 DROP: self.dropCalculator}
        self.suitCalculators = {}
        self.toonAtkOrder = []
        self.toonSkillPtsGained = {}
        self.__clearBonuses()
        self.__skillCreditMultiplier = 1
        self.tutorialFlag = tutorialFlag
        self.accept('add-exp', self.__addAttackExp)

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

    def createSuitCalc(self, suit):
        if suit.dna.name in SpecialCalculators:
            # This will import the special SuitCalculator for this specific suit
            calc = importlib.import_module(SpecialCalcDir + '.' + SpecialCalculators[suit.dna.name])
        else:
            calc = DefaultSuitCalculatorAI
        self.suitCalculators[suit.getDoId()] = calc.SuitCalculatorAI(self.battle, suit, self.healCalculator)

    def getSuitCalc(self, suit):
        if suit in self.battle.activeSuits:
            suitId = suit.getDoId()
            if suitId in self.suitCalculators.keys():
                return self.suitCalculators[suitId]
        return None


    def getSuitCalc(self, suit):
        if suit in self.battle.activeSuits:
            suitId = suit.getDoId()
            if suitId in self.suitCalculators.keys():
                return self.suitCalculators[suitId]
        return None

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
        self.__findToonAttacks()

        self.notify.debug('Toon attack order: ' + str(self.toonAtkOrder))
        self.notify.debug('Active toons: ' + str(self.battle.activeToons))
        self.notify.debug('Toon attacks: ' + str(self.battle.toonAttacks))
        self.notify.debug('Active suits: ' + str(self.battle.activeSuits))
        self.notify.debug('Suit attacks: ' + str(self.battle.suitAttacks))

        self.__clearBonuses()
        self.__updateActiveToons()
        messenger.send('init-round')
        messenger.send('init-round-order', [self.toonAtkOrder])
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
            atkTrack = getActualTrack(attack)
            if atkTrack not in [NO_ATTACK, SOS, NPCSOS]:
                if BCG.SUITS_WAKE_IMMEDIATELY and currTrack and atkTrack != currTrack:
                    self.lureCalculator.wakeDelayedLures()
                currTrack = atkTrack
                self.notify.debug('Calculating attack for toon: %d' % toonId)
                self.__calcToonAttackHp(toonId)
                attackIdx = self.toonAtkOrder.index(toonId)
                self.__handleBonus(attackIdx)
                lastAttack = attackIdx >= len(self.toonAtkOrder) - 1
                if attackHasHit(attack, suit=0) and atkTrack in [THROW, SQUIRT, SOUND, ZAP]:
                    if lastAttack:
                        self.lureCalculator.wakeSuitFromAttack(self, toonId)
                    else:
                        messenger.send('delayed-wake', [toonId])
                if attackIdx >= len(self.toonAtkOrder) - 1:
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

        for suitCalculator in self.suitCalculators.values():
            suitCalculator.clearMissingAttackers()

        messenger.send('update-active-toons')

        for suit in self.trapCalculator.trappedSuits:
            trapStatus = suit.getStatus(TRAPPED_STATUS)
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
        atkTrack, atkLevel = getActualTrackLevel(attackId)
        if atkTrack == NPCSOS or atkTrack == FIRE:
            return 1
        if atkTrack == TRAP:
            attackId[TOON_MISSED_COL] = 0
            return 1
        if atkTrack == PETSOS:
            return calculatePetTrickSuccess(attackId)
        if atkTrack == ZAP:
            currAtk = self.toonAtkOrder.index(attackIndex)
            prevAtkTrack, prevAttack = self.__getPreviousAttack(currAtk)
            attackId[TOON_MISSED_COL] = self.zapCalculator.calcZapHit(attackIndex, atkTargets[0],
                                                                      currAtk, prevAttack, prevAtkTrack)
            return not attackId[TOON_MISSED_COL]

        tgtDef = 0
        highestDecay = 0
        if atkTrack not in HEALING_TRACKS:
            highestDecay, tgtDef = findLowestDefense(atkTargets, tgtDef)

        trackExp = self.__checkTrackAccBonus(attackId[TOON_ID_COL], atkTrack)
        trackExp = self.__findHighestTrackBonus(atkTrack, attackId, trackExp)

        if atkTrack in ACC_UP_TRACKS:
            propAcc = self.dropCalculator.calcAccBonus(attackId, atkLevel)
        else:
            propAcc = AvPropAccuracy[atkTrack][atkLevel]

        attackAcc = propAcc + trackExp + tgtDef

        currAtk = self.toonAtkOrder.index(attackIndex)
        if currAtk > 0 and atkTrack != HEAL:
            prevAtkTrack, prevAttack = self.__getPreviousAttack(currAtk)
            if atkTrack == prevAtkTrack and (attackId[TOON_TGT_COL] == prevAttack[TOON_TGT_COL]):
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
            self.notify.debug('HIT: Toon attack rolled ' + str(randChoice) + ' to hit with an accuracy of ' + str(acc))
            attackId[TOON_MISSED_COL] = 0
        else:
            self.notify.debug('MISS: Toon attack rolled ' + str(randChoice) + ' to hit with an accuracy of ' + str(acc))
            attackId[TOON_MISSED_COL] = 1
        return not attackId[TOON_MISSED_COL]

    def __calcPrevAttackBonus(self, attackKey):
        numPrevHits = 0
        attackIdx = self.toonAtkOrder.index(attackKey)
        for currPrevAtk in xrange(attackIdx - 1, -1, -1):
            attack = self.battle.toonAttacks[attackKey]
            atkTrack, atkLevel = getActualTrackLevel(attack)
            prevAttackKey = self.toonAtkOrder[currPrevAtk]
            prevAttack = self.battle.toonAttacks[prevAttackKey]
            prvAtkTrack, prvAtkLevel = getActualTrackLevel(prevAttack)
            if (attackHasHit(prevAttack)
                    and (attackAffectsGroup(prvAtkTrack, prvAtkLevel, prevAttack[TOON_TRACK_COL])
                         or attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL])
                         or attack[TOON_TGT_COL] == prevAttack[TOON_TGT_COL])
                    and atkTrack != prvAtkTrack):
                numPrevHits += 1

        if numPrevHits > 0:
            self.notify.debug('ACC BONUS: toon attack received accuracy bonus of ' +
                              str(BCG.AccuracyBonuses[numPrevHits]) + ' from previous attack')
        return BCG.AccuracyBonuses[numPrevHits]

    def __findHighestTrackBonus(self, atkTrack, attack, trackExp):
        for currOtherAtk in self.toonAtkOrder:
            if currOtherAtk != attack[TOON_ID_COL]:
                nextAttack = self.battle.toonAttacks[currOtherAtk]
                nextAtkTrack = getActualTrack(nextAttack)
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
        prevAtkTrack = getActualTrack(prevAttack)
        return prevAtkTrack, prevAttack

    # TOON DAMAGE/SUCCESS CALCULATION ==================================================================================

    def __calcToonAttackHp(self, toonId):
        attack = self.battle.toonAttacks[toonId]
        targetList = createToonTargetList(self.battle, toonId)
        atkHit = self.__calcToonAttackHit(toonId, targetList)
        atkTrack = getActualTrack(attack)
        if not atkHit and atkTrack != HEAL:
            return

        if atkTrack in self.trackCalculators:
            targetsExist = self.trackCalculators[atkTrack].calcAttackResults(attack, toonId)
        else:
            targetsExist = self.calcAttackResults(attack, toonId)

        if not targetsExist and self.__prevAtkTrack(toonId) != atkTrack:
            self.notify.debug('Something happened to our target!  Removing attack...')
            self.__clearAttack(toonId)
        return

    def calcAttackResults(self, attack, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack)
        if atkTrack in HEALING_TRACKS:
            targets = self.battle.activeToons
        else:
            targets = self.battle.activeSuits
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        results = [0 for _ in xrange(len(targets))]
        targetsExist = 0
        for target in targetList:
            result = 0
            if atkTrack == PETSOS:
                result = atkHp
            elif atkTrack == FIRE:
                result = 0
                if target:
                    costToFire = target.level // 3
                    abilityToFire = toon.getPinkSlips()
                    toon.removePinkSlips(costToFire)
                    if costToFire <= abilityToFire:
                        target.skeleRevives = 0
                        result = target.getHP()

            if atkTrack in HEALING_TRACKS:
                targetsExist += self.healCalculator.getToonHp(target) > 0
            else:
                targetsExist += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, result))

            if result != 0:
                if target in targets:
                    results[targets.index(target)] = result
                else:
                    self.notify.debug("The target is not accessible!")
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
        self.__clearBonuses()
        for currentToon in self.toonAtkOrder:
            if currentToon != -1:
                self.__applyAttack(currentToon, lastAttacks, lastTrack)

    def __applyAttack(self, currentToon, lastAttacks, lastTrack):
        attack = self.battle.toonAttacks[currentToon]
        atkTrack, atkLevel = getActualTrackLevel(attack)
        if atkTrack not in [HEAL, NO_ATTACK] + SOS_TRACKS:
            targets = createToonTargetList(self.battle, currentToon)
            allTargetsDead = 1
            for suit in targets:
                damageDone = getMostDamage(attack)
                if damageDone > 0:
                    messenger.send('toon-threat', [attack[TOON_ID_COL], damageDone])
                if atkTrack == TRAP:
                    if suit in self.trapCalculator.trappedSuits:
                        trapInfo = suit.getStatus(TRAPPED_STATUS)
                        suit.battleTrap = trapInfo['level']
                targetDead = 0
                if suit.getHP() > 0:
                    allTargetsDead = 0
                else:
                    targetDead = 1
                    if atkTrack != LURE:
                        for currLastAtk in lastAttacks:
                            self.__clearTgtDied(suit, currLastAtk, attack)

                if targetDead and atkTrack != lastTrack:
                    tgtPos = self.battle.activeSuits.index(suit)
                    attack[TOON_HP_COL][tgtPos] = 0
                    attack[TOON_KBBONUS_COL][tgtPos] = -1

            if allTargetsDead and atkTrack != lastTrack:
                if self.notify.getDebug():
                    self.notify.debug('all targets of toon attack ' + str(currentToon) + ' are dead')
                self.__clearAttack(currentToon)
                attack = self.battle.toonAttacks[currentToon]
                atkTrack, atkLevel = getActualTrackLevel(attack)

        damagesDone = self.__applyToonAttackDamages(currentToon)
        if atkTrack not in [LURE, ZAP]:
            self.__applyToonAttackDamages(currentToon, hpBonus=1)
            if atkTrack in [THROW, SQUIRT]:
                self.__applyToonAttackDamages(currentToon, kbBonus=1)
        if lastTrack != atkTrack:
            lastAttacks = []
        lastAttacks.append(attack)
        if atkTrack != PETSOS and atkLevel < self.creditLevel:
            if atkTrack in [TRAP, LURE]:
                pass
            elif damagesDone:
                self.__addAttackExp(attack)

    def __applyToonAttackDamages(self, toonId, hpBonus=0, kbBonus=0):
        totalDamages = 0
        if not APPLY_HEALTH_ADJUSTMENTS:
            return totalDamages
        attack = self.battle.toonAttacks[toonId]
        track = getActualTrack(attack)
        if track not in [NO_ATTACK, SOS, TRAP, NPCSOS]:
            if track in BCG.HEALING_TRACKS:
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
                if track in BCG.HEALING_TRACKS:
                    excess = self.healCalculator.healToon(attack, damageDone, target, position)
                    if excess:
                        damageDone -= excess
                    self.notify.debug(str(target) + ': toon takes ' + str(damageDone) + ' healing')
                else:
                    targetId = target.getDoId()
                    calc = self.getSuitCalc(target)
                    if calc:
                        calc.hitSuit(attack, damageDone)
                    if hpBonus:
                        self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage from HP-Bonus')
                    elif kbBonus:
                        self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage from KB-Bonus')
                    else:
                        self.notify.debug(str(targetId) + ': suit takes ' + str(damageDone) + ' damage')
                    if target.getHP() <= 0:
                        if target.getSkeleRevives() >= 1:
                            target.useSkeleRevive()
                            attack[SUIT_REVIVE_COL] = attack[SUIT_REVIVE_COL] | 1 << position
                        else:
                            self.suitLeftBattle(target)
                            attack[SUIT_DIED_COL] = attack[SUIT_DIED_COL] | 1 << position
                            self.notify.debug('Suit ' + str(targetId) + ' bravely expired in combat')
                            messenger.send('suit-killed', [target])
                totalDamages += damageDone
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
        atkDmg = getMostDamage(attack)
        atkTrack = getActualTrack(attack)
        if atkTrack not in [LURE, ZAP] or atkDmg > 0:
            self.__addDmgToBonuses(attackIdx)
            if atkTrack in [THROW, SQUIRT]:
                self.__addDmgToBonuses(attackIdx, hpBonus=0)

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
                                    if self.battle.getToon(toonId).getTrackPrestige(DROP):
                                        numOrgs += 1

                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (BCG.DropDamageBonuses[numOrgs][
                                                        attackCount - 1] * 0.01))
                            else:
                                attack[TOON_HPBONUS_COL][targetPos] = math.ceil(
                                    totalDamages * (BCG.DamageBonuses[attackCount - 1] * 0.01))
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

    def __addDmgToBonuses(self, attackIndex, hpBonus=1):
        toonId = self.toonAtkOrder[attackIndex]
        attack = self.battle.toonAttacks[toonId]
        atkTrack = getActualTrack(attack)
        if atkTrack == HEAL or atkTrack == PETSOS:
            return
        hps = attack[TOON_HP_COL]
        for i in xrange(len(hps)):
            currTgt = self.battle.suits[i]
            dmg = hps[i]
            if hpBonus and dmg > 0:
                self.__addBonus(attackIndex, self.hpBonuses[i], dmg, atkTrack)
            elif currTgt.getStatus(LURED_STATUS) and dmg > 0:
                self.__addBonus(attackIndex, self.kbBonuses[i], dmg, atkTrack)

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
        currAtkTrack = getActualTrack(currAtk)
        lastAtkTrack = getActualTrack(lastAtk)
        if currAtkTrack == lastAtkTrack and lastAtk[SUIT_DIED_COL] & 1 << position and \
                attackHasHit(currAtk, suit=0):
            self.notify.debug('Clearing suit died for ' + str(tgt.getDoId()) + ' at position ' + str(
                    position) + ' from toon attack ' + str(lastAtk[TOON_ID_COL]) + ' and setting it for ' + str(
                    currAtk[TOON_ID_COL]))
            lastAtk[SUIT_DIED_COL] = lastAtk[SUIT_DIED_COL] ^ 1 << position
            self.suitLeftBattle(tgt)
            currAtk[SUIT_DIED_COL] = currAtk[SUIT_DIED_COL] | 1 << position

    # EXPERIENCE CALCULATION ===========================================================================================

    def __addAttackExp(self, attack, attackTrack=-1, attackLevel=-1, attackerId=-1):
        track = -1
        level = -1
        toonId = -1
        if attackTrack != -1 and attackLevel != -1 and attackerId != -1:
            track = attackTrack
            level = attackLevel
            toonId = attackerId
        elif attackHasHit(attack):
            self.notify.debug('Attack %s has hit' % repr(attack))
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
        for suit in self.battle.activeSuits:
            calc = self.getSuitCalc(suit)
            if calc:
                calc.calcSuitAttack()

    # BATTLE ESCAPE FUNCTIONS ==========================================================================================

    def toonLeftBattle(self, toonId):
        self.notify.debug('toonLeftBattle()' + str(toonId))
        if toonId in self.toonSkillPtsGained:
            del self.toonSkillPtsGained[toonId]
        for suitCalculator in self.suitCalculators.values():
            suitCalculator.removeAttacker(toonId)
            suitCalculator.removeAttackStats(toonId)

        self.trapCalculator.clearTrapCreator(toonId)

    def suitLeftBattle(self, suit):
        suitId = suit.getDoId()
        self.notify.debug('suitLeftBattle(): ' + str(suitId))
        self.lureCalculator.removeLureStatus(suit)
        self.trapCalculator.removeTrapStatus(suit)
        self.squirtCalculator.removeSoakStatus(suit)
        self.throwCalculator.removeMarkStatus(suit)
        if suitId in self.suitCalculators.keys():
            self.suitCalculators[suitId].cleanup()
            del self.suitCalculators[suitId]


    # VARIOUS PROPERTY GETTERS =========================================================================================

    def __prevAtkTrack(self, attackerId):
        prevAtkIdx = self.toonAtkOrder.index(attackerId) - 1
        if prevAtkIdx >= 0:
            prevAttackerId = self.toonAtkOrder[prevAtkIdx]
            attack = self.battle.toonAttacks[prevAttackerId]
            return getActualTrack(attack)
        else:
            return NO_ATTACK
