from otp.avatar import Avatar
from direct.directnotify import DirectNotifyGlobal
from direct.interval.IntervalGlobal import *

class BattleAvatar(Avatar.Avatar):
    
    def __init__(self):
        self.battle = None
        self.statusEffects = []
    
    def setBattle(self, battle):
        self.battle = battle