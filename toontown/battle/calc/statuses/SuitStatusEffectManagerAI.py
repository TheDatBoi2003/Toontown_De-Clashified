from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger

from toontown.battle.calc.BattleCalculatorGlobals import *


class SuitStatusEffectManager(DirectObject):
    
    def __init__(self, suit):
        
        