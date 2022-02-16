from otp.otpbase.PythonUtil import lerp
from toontown.battle.BattleBase import *
from toontown.battle.SuitBattleGlobals import *
from toontown.pets import PetTricks
from toontown.toonbase.ToontownBattleGlobals import *

AccuracyBonuses = [0, 20, 40, 60]
DamageBonuses = [0, 20, 20, 20]
DropDamageBonuses = [[0, 20, 30, 40], [0, 30, 40, 50], [0, 40, 50, 60], [0, 50, 60, 70]]
AttackExpPerTrack = [0, 10, 20, 30, 40, 50, 60, 70]
NumRoundsLured = AvLureRounds
NumRoundsSoaked = AvSoakRounds
HEALING_TRACKS = [HEAL, PETSOS]
TRAP_CONFLICT = -2
APPLY_HEALTH_ADJUSTMENTS = 1
TOONS_TAKE_NO_DAMAGE = 0
CAP_HEALS = 1
CLEAR_SUIT_ATTACKERS = 1
SUITS_WAKE_IMMEDIATELY = 1
FIRST_TRAP_ONLY = 0
KB_BONUS_LURED_FLAG = 0
KB_BONUS_TGT_LURED = 1
SpecialCalcDir = 'toontown.battle.calc.special'
SpecialCalculators = {'foreman': 'ForemanCalculatorAI'}

notify = DirectNotifyGlobal.directNotify.newCategory('BattleCalculatorGlobals')
PropAndPrestigeStack = simbase.config.GetBool('prop-and-organic-bonus-stack', 0)


def createToonTargetList(battle, attackIndex):
    attack = battle.toonAttacks[attackIndex]
    atkTrack, atkLevel = getActualTrackLevel(attack)
    targetList = []
    if atkTrack == NPCSOS:
        return targetList
    if not attackAffectsGroup(atkTrack, atkLevel, attack[TOON_TRACK_COL]):
        if atkTrack == HEAL:
            target = attack[TOON_TGT_COL]
        else:
            target = battle.findSuit(attack[TOON_TGT_COL])
        if target:
            targetList.append(target)
    else:
        if atkTrack in HEALING_TRACKS:
            if attack[TOON_TRACK_COL] == NPCSOS or atkTrack == PETSOS:
                targetList = battle.activeToons
            else:
                for currToon in battle.activeToons:
                    if attack[TOON_ID_COL] != currToon:
                        targetList.append(currToon)
        else:
            targetList = battle.activeSuits
    return targetList


def attackHasHit(attack, suit=0):
    if suit:
        for dmg in attack[SUIT_HP_COL]:
            if dmg > 0:
                return 1
        return 0
    else:
        track = getActualTrack(attack)
        return not attack[TOON_MISSED_COL] and track != NO_ATTACK


def getMostDamage(attack):
    mostDamage = 0
    for hp in attack[TOON_HP_COL]:
        if hp > mostDamage:
            mostDamage = hp
    return mostDamage


def findLowestDefense(atkTargets, tgtDef):
    highestDecay = 0
    for currTarget in atkTargets:
        thisSuitDef = getTargetDefense(currTarget)
        notify.debug('Examining suit def for toon attack: ' + str(thisSuitDef))
        tgtDef = min(thisSuitDef, tgtDef)
        status = currTarget.getStatus(LURED_STATUS)
        if status:
            highestDecay = max(highestDecay, status['decay'])
    notify.debug('Suit defense used for toon attack: ' + str(tgtDef))
    return highestDecay, tgtDef


def receiveDamageCalc(atkLevel, atkTrack, target, toon):
    if toon and toon.getInstaKill():
        attackDamage = target.getHP()
    else:
        attackDamage = doDamageCalc(atkLevel, atkTrack, toon)
    return attackDamage


def doDamageCalc(atkLevel, atkTrack, toon):
    damage = getAvPropDamage(atkTrack, atkLevel, toon.experience.getExp(atkTrack))
    return damage


def getToonPrestige(battle, toonId, track):
    toon = battle.getToon(toonId)
    if toon:
        return toon.checkTrackPrestige(track)
    else:
        return False


def getToonPropBonus(battle, track):
    return battle.getInteractivePropTrackBonus() == track


def getActualTrack(toonAttack):
    if toonAttack[TOON_TRACK_COL] == NPCSOS:
        track = NPCToons.getNPCTrack(toonAttack[TOON_TGT_COL])
        if track is not None:
            return track
        else:
            notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
    return toonAttack[TOON_TRACK_COL]


def getActualTrackLevel(toonAttack):
    if toonAttack[TOON_TRACK_COL] == NPCSOS:
        track, level, hp = NPCToons.getNPCTrackLevelHp(toonAttack[TOON_TGT_COL])
        if track is not None:
            return track, level
        else:
            notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
    return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL]


def getActualTrackLevelHp(toonAttack):
    if toonAttack[TOON_TRACK_COL] == NPCSOS:
        track, level, hp = NPCToons.getNPCTrackLevelHp(toonAttack[TOON_TGT_COL])
        if track:
            return track, level, hp
        else:
            notify.warning('No NPC with id: %d' % toonAttack[TOON_TGT_COL])
    elif toonAttack[TOON_TRACK_COL] == PETSOS:
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
            notify.warning('pet proxy: %d not in doId2do!' % petProxyId)
        return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL], hp
    return toonAttack[TOON_TRACK_COL], toonAttack[TOON_LVL_COL], 0


def calculatePetTrickSuccess(toonAttack):
    petProxyId = toonAttack[TOON_TGT_COL]
    if petProxyId not in simbase.air.doId2do:
        notify.warning('pet proxy %d not in doId2do!' % petProxyId)
        toonAttack[TOON_MISSED_COL] = 1
        return 0
    petProxy = simbase.air.doId2do[petProxyId]
    trickId = toonAttack[TOON_LVL_COL]
    toonAttack[TOON_MISSED_COL] = petProxy.attemptBattleTrick(trickId)
    if toonAttack[TOON_MISSED_COL] == 1:
        return 0
    else:
        return 1


def getHighestTargetLevel(battle):
    maxSuitLevel = 0
    for suit in battle.activeSuits:
        maxSuitLevel = max(maxSuitLevel, suit.getActualLevel())
    return maxSuitLevel


def getTargetDefense(suit):
    suitDef = SuitBattleGlobals.SuitAttributes[suit.dna.name]['def'][suit.getLevel()]
    suitDef += 5 * suit.isExecutive
    for status in suit.statuses:
        if 'defense' in status:
            suitDef += status['defense']
    return -suitDef


def getLureRounds(suit):
    lured = suit.getStatus(SuitBattleGlobals.LURED_STATUS)
    if lured:
        return lured['rounds']
    return -1

