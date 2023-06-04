from direct.interval.IntervalGlobal import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
from toontown.battle.BattleBase import *
from direct.directnotify import DirectNotifyGlobal
import MovieCamera
import random
import MovieUtil
import toontown.battle.movies.BattleParticles
from libotp import CFSpeech, CFTimeout
from toontown.toonbase import TTLocalizer
from toontown.toonbase.ToontownBattleGlobals import AvPropDamage
from toontown.toon import NPCToons
import MovieNPCSOS
from toontown.effects import Splash
from attacks.ToonUpGags import *

notify = DirectNotifyGlobal.directNotify.newCategory('MovieHeal')


def doHeals(heals):
    if len(heals) == 0:
        return None, None
    track = Sequence()
    for heal in heals:
        for target in heal['target']:
            if heal['toon'] == target['toon']:
                heal['toon'].toonUp(target['hp'])
        interval = __doHealLevel(heal)
        if interval:
            track.append(interval)

    camDuration = track.getDuration()
    camTrack = MovieCamera.chooseHealShot(heals, camDuration)
    return track, camTrack


def __doHealLevel(heal):
    level = heal['level']
    healing_items = {
        0: Feather,
        1: Megaphone,
        2: Lipstick,
        3: BambooCane,
        4: PixieDust,
        5: JugglingCubes,
        6: PixieDust,
        7: HighDive
    }
    healing_item_class = healing_items.get(level)
    return healing_item_class(heal) if healing_item_class else None
