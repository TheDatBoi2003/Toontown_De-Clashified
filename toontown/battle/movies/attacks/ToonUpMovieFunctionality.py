from direct.interval.IntervalGlobal import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
from toontown.battle.BattleBase import *
from direct.directnotify import DirectNotifyGlobal
import random
import toontown.battle.movies.MovieUtil
import toontown.battle.movies.BattleParticles
from libotp import CFSpeech, CFTimeout
from toontown.toonbase import TTLocalizer
from toontown.toonbase.ToontownBattleGlobals import AvPropDamage
from toontown.toon import NPCToons
import toontown.battle.movies.MovieNPCSOS
from toontown.effects import Splash
from ToonUpGags import *

notify = DirectNotifyGlobal.directNotify.newCategory('ToonUpMovieFunctionality')
toonHealJokes = TTLocalizer.ToonHealJokes

soundFiles = (
    'AA_heal_tickle.ogg',
    'AA_heal_telljoke.ogg',
    'AA_heal_smooch.ogg',
    'AA_heal_happydance.ogg',
    'AA_heal_pixiedust.ogg',
    'AA_heal_juggle.ogg',
    'AA_heal_pixiedust.ogg',
    'AA_heal_High_Dive.ogg')
healPos = Point3(0, 0, 0)
healHpr = Vec3(180.0, 0, 0)

runHealTime = 1.0

def runToHealSpot(heal):
    toon = heal['toon']
    battle = heal['battle']
    level = heal['level']
    origPos, origHpr = battle.getActorPosHpr(toon)
    runAnimI = ActorInterval(toon, 'run', duration=runHealTime)
    a = Func(toon.headsUp, battle, healPos)
    b = Parallel(runAnimI, LerpPosInterval(toon, runHealTime, healPos, other=battle))
    if levelAffectsGroup(HEAL, level):
        c = Func(toon.setHpr, battle, healHpr)
    else:
        target = heal['target'][0]['toon']
        targetPos = target.getPos(battle)
        c = Func(toon.headsUp, battle, targetPos)
    return Sequence(a, b, c)


def returnToBase(heal):
    toon = heal['toon']
    battle = heal['battle']
    origPos, origHpr = battle.getActorPosHpr(toon)
    runAnimI = ActorInterval(toon, 'run', duration=runHealTime)
    a = Func(toon.headsUp, battle, origPos)
    b = Parallel(runAnimI, LerpPosInterval(toon, runHealTime, origPos, other=battle))
    c = Func(toon.setHpr, battle, origHpr)
    d = Func(toon.loop, 'neutral')
    return Sequence(a, b, c, d)


def healToon(toon, hp, ineffective):
    notify.debug('healToon() - toon: %d hp: %d ineffective: %d' % (toon.doId, hp, ineffective))
    if ineffective == 1:
        laughter = random.choice(TTLocalizer.MovieHealLaughterMisses)
    else:
        maxDam = AvPropDamage[0][1][0][1]
        if hp >= maxDam - 1:
            laughter = random.choice(TTLocalizer.MovieHealLaughterHits2)
        else:
            laughter = random.choice(TTLocalizer.MovieHealLaughterHits1)
    toon.setChatAbsolute(laughter, CFSpeech | CFTimeout)
    if hp > 0 and toon.hp:
        toon.toonUp(hp)
    else:
        notify.debug('healToon() - toon: %d hp: %d' % (toon.doId, hp))
    return


def getPartTrack(particleEffect, startDelay, durationDelay, partExtraArgs):
    pEffect = partExtraArgs[0]
    parent = partExtraArgs[1]
    if len(partExtraArgs) == 3:
        worldRelative = partExtraArgs[2]
    else:
        worldRelative = 1
    return Sequence(Wait(startDelay),
                    ParticleInterval(pEffect, parent, worldRelative, duration=durationDelay, cleanup=True))


def getSoundTrack(level, delay, duration=None, node=None):
    soundEffect = globalBattleSoundCache.getSound(soundFiles[level])
    soundIntervals = Sequence()
    if soundEffect:
        if duration:
            playSound = SoundInterval(soundEffect, duration=duration, node=node)
        else:
            playSound = SoundInterval(soundEffect, node=node)
        soundIntervals.append(Wait(delay))
        soundIntervals.append(playSound)
    return soundIntervals

def add3(t1, t2):
    returnThree = Point3(t1[0] + t2[0], t1[1] + t2[1], t1[2] + t2[2])
    return returnThree


def stopLook(toonsInBattle):
    for someToon in toonsInBattle:
        someToon.stopStareAt()


def toonsLook(toons, someNode, offset):
    for someToon in toons:
        someToon.startStareAt(someNode, offset)