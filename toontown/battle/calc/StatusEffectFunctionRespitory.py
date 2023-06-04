from StatusGlobal import *
from BattleCalculatorGlobals import *

def getFunctionFromRespitory(av, statusBaser, statusValue):
    if statusBaser == DAMAGE_UP:
        return applyDamageBuff(av,statusValue)
    elif statusBaser == DAMAGE_DOWN:
        return removeDamageBuff(av,statusValue)

def getDoneFunctionFromRespitory(av, statusBaser, statusValue):
    if statusBaser == DAMAGE_UP:
        return removeDamageBuff(av, statusValue)

def applyDamageBuff(av, statusValue):
    av.damageBonus += statusValue

def removeDamageBuff(av, statusValue):
    av.damageBonus -= statusValue