from math import ceil

from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *


class SoundCalculatorAI(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory('SoundCalculatorAI')

    def __init__(self, battle):
        DirectObject.__init__(self)
        self.battle = battle

    def cleanup(self):
        pass

    def calcAttackResults(self, attack, toonId):
        atkTrack, atkLevel, atkHp = getActualTrackLevelHp(attack)
        targetList = createToonTargetList(self.battle, toonId)
        toon = self.battle.getToon(toonId)
        prestige, propBonus = toon.getTrackPrestige(atkTrack), getToonPropBonus(self.battle, atkTrack)
        suits = self.battle.activeSuits
        results = [0 for _ in xrange(len(suits))]
        targetsHit = 0
        if prestige or propBonus:
            highestLevel = max(target.getActualLevel() for target in targetList) + 1
            if PropAndPrestigeStack and prestige and propBonus:
                bonusDamage = int(highestLevel)
            else:
                bonusDamage = int(ceil(highestLevel * 0.5))
        else:
            bonusDamage = 0

        for target in targetList:
            if target not in suits:
                self.notify.debug("The target is not accessible!")
                continue

            attackDamage = receiveDamageCalc(atkLevel, atkTrack, target, toon) + bonusDamage

            targetsHit += target.getHP() > 0

            self.notify.debug('%d targets %s, result: %d' % (toonId, target, attackDamage))

            if target.getStatus(LURED_STATUS):
                self.notify.debug('Sound on lured suit, ' + 'indicating with KB_BONUS_COL flag')
                pos = suits.index(target)
                attack[TOON_KBBONUS_COL][pos] = KB_BONUS_LURED_FLAG
                messenger.send('delayed-wake', [toonId, target])
                messenger.send('lured-hit-exp', [attack, target])

            results[suits.index(target)] = attackDamage
        attack[TOON_HP_COL] = results  # <--------  THIS IS THE ATTACK OUTPUT!
        return targetsHit > 0
