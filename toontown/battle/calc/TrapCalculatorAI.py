from direct.showbase.DirectObject import DirectObject

from toontown.battle.calc.BattleCalculatorGlobals import *
from toontown.toonbase.ToontownBattleGlobals import RAILROAD_LEVEL_INDEX


class TrapCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('TrapCalculatorAI')

    def __init__(self, battle, statusCalculator):
        DirectObject.__init__(self)
        self.trappedSuits = []  # Keeps track of trapped suits over a longer period of time
        self.trapCollisions = []  # Keeps track of trap collisions for the current turn
        self.battle = battle
        self.statusCalculator = statusCalculator
        self.trainTrapTriggered = False
        self.accept('init-round', self.__resetFields)

    def cleanup(self):
        self.ignoreAll()

    def calcAttackResults(self, attack, targets, toonId):
        atkLevel = attack[TOON_LVL_COL]
        targetList = createToonTargetList(self.battle, toonId)
        npcSOS = attack[TOON_TRACK_COL] == NPCSOS
        npcDamage = 0
        if npcSOS:
            npcDamage = NPCToons.getNPCHp(attack[TOON_TGT_COL])
        results = [0 for _ in xrange(len(targets))]
        trappedSuits = 0

        if atkLevel == RAILROAD_LEVEL_INDEX or npcSOS:
            kbBonuses = attack[TOON_KBBONUS_COL]
            results, trappedSuits = self.__groupTrapSuits(atkLevel, toonId, targetList, kbBonuses, npcDamage)
        else:
            for target in targetList:
                result = 0
                if FIRST_TRAP_ONLY and self.getSuitTrapType(target) != NO_TRAP:
                    self.__clearTrap(toonId)
                else:
                    result = self.__trapSuit(target, atkLevel, toonId, npcDamage)

                trappedSuits += target.getHP() > 0

                self.notify.debug('%d targets %s, result: %d' % (toonId, target, result))

                if result != 0:
                    if target not in targets:
                        self.notify.debug("The suit is not accessible!")
                        continue

                    results[targets.index(target)] = result

        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return trappedSuits > 0

    def getSuitTrapType(self, suit):
        suitId = suit.getDoId()
        trapStatus = suit.getStatus(TRAPPED_STATUS)
        if trapStatus:
            if suitId in self.trapCollisions:
                self.notify.debug('%s used to have a trap, but it was removed.' % suitId)
                return NO_TRAP
            else:
                self.notify.debug('%s is currently trapped!' % suitId)
                return trapStatus['level']
        else:
            self.notify.debug('%s has no trap.' % suitId)
            return NO_TRAP

    def removeTrapStatus(self, suit):
        if suit in self.trappedSuits:
            self.trappedSuits.remove(suit)
            self.statusCalculator.removeStatus(suit, statusName=TRAPPED_STATUS)

    def clearTrapCreator(self, creatorId, suit=None):
        if not suit:
            for suit in self.trappedSuits:
                trapStatus = suit.getStatus(TRAPPED_STATUS)
                if trapStatus['toon'] == creatorId:
                    trapStatus['toon'] = 0
            return
        trapStatus = suit.getStatus(TRAPPED_STATUS)
        if trapStatus:
            trapStatus['toon'] = 0

    @staticmethod
    def getTrapInfo(suit):
        if SuitStatusNames[2] in suit.statuses:
            trapStatus = suit.getStatus(TRAPPED_STATUS)
            attackLevel = trapStatus['level']
            attackDamage = trapStatus['damage']
            trapCreatorId = trapStatus['toon']
        else:
            attackLevel = NO_TRAP
            attackDamage = 0
            trapCreatorId = 0
        return attackDamage, attackLevel, trapCreatorId

    def __trapSuit(self, suit, trapLvl, attackerId, npcDamage=0):
        if not npcDamage:
            if suit.getStatus(TRAPPED_STATUS):
                self.__checkTrapConflict(suit.doId)
            else:
                self.__applyTrap(attackerId, suit, trapLvl)
        else:
            self.__applyNPCTrap(npcDamage, suit, trapLvl)

        if suit.doId in self.trapCollisions:
            self.notify.debug('There were two traps that collided! Removing the traps now.')
            self.removeTrapStatus(suit)
            result = 0
        else:
            result = TRAPPED_STATUS in suit.statuses
        return result

    def __groupTrapSuits(self, trapLvl, attackerId, allSuits, kbBonuses, npcDamage=0):
        trappedSuits = 0
        results = []
        for suit in allSuits:
            suitId = suit.getDoId()
            if not npcDamage:
                if suit.getStatus(TRAPPED_STATUS):
                    self.__checkTrapConflict(suitId, allSuits)
                else:
                    self.__applyTrap(attackerId, suitId, trapLvl)
                if trapLvl == RAILROAD_LEVEL_INDEX:
                    if suit.getStatus(LURED_STATUS):
                        self.notify.debug(
                            'Train Trap on lured suit %d, \n indicating with KB_BONUS_COL flag' % suit.getDoId())
                        tgt_pos = self.battle.activeSuits.index(suit)
                        kbBonuses[tgt_pos] = KB_BONUS_LURED_FLAG
            else:
                self.__applyNPCTrap(npcDamage, suit, trapLvl)

            if suit.doId in self.trapCollisions:
                self.notify.debug('There were two traps that collided! Removing the traps now.')
                self.removeTrapStatus(suit)
                results.append(0)
            else:
                trapped = TRAPPED_STATUS in suit.statuses
                results.append(trapped)
                trappedSuits += trapped
        return results, trappedSuits > 0

    def __applyTrap(self, toonId, suit, trapLvl):
        toon = self.battle.getToon(toonId)
        damage = getTrapDamage(trapLvl, toon, suit)
        self.notify.debug('%s places a %s damage trap!' % (toonId, damage))
        if trapLvl < getHighestTargetLevel(self.battle):
            self.__addTrapStatus(suit, trapLvl, damage, toonId)
        else:
            self.__addTrapStatus(suit, trapLvl, damage)

    def __applyNPCTrap(self, npcDamage, suit, trapLvl):
        self.notify.debug('An NPC places a trap!')
        if suit in self.trapCollisions:
            self.__addTrapStatus(suit, trapLvl, npcDamage)
        else:
            if not suit.getStatus(TRAPPED_STATUS):
                self.__addTrapStatus(suit, trapLvl, npcDamage)

    def __addTrapStatus(self, suit, level=-1, damage=0, toonId=-1):
        trapStatus = genSuitStatus(TRAPPED_STATUS)
        trapStatus['level'] = level
        trapStatus['damage'] = damage
        trapStatus['toon'] = toonId
        self.notify.debug('%s now has a level %d trap that deals %d damage.' % (suit.doId, level, damage))
        suit.b_addStatus(trapStatus)
        self.trappedSuits.append(suit)

    def __checkTrapConflict(self, suitId, allSuits=None):
        if suitId not in self.trapCollisions:
            self.trapCollisions.append(suitId)
        if allSuits:
            for suit in allSuits:
                if suit.getStatus(TRAPPED_STATUS) and suit.doId not in self.trapCollisions:
                    self.trapCollisions.append(suitId)

    def __clearTrap(self, attackIdx):
        self.notify.debug('clearing out toon attack for toon ' + str(attackIdx) + '...')
        self.battle.toonAttacks[attackIdx] = getToonAttack(attackIdx)
        longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
        for j in xrange(longest):
            self.battle.toonAttacks[attackIdx][TOON_HP_COL].append(-1)
            self.battle.toonAttacks[attackIdx][TOON_HPBONUS_COL].append(-1)
            self.battle.toonAttacks[attackIdx][TOON_KBBONUS_COL].append(-1)
        self.notify.debug('toon attack is now ' + repr(self.battle.toonAttacks[attackIdx]))

    def __resetFields(self):
        self.trapCollisions = []
        self.trainTrapTriggered = False
