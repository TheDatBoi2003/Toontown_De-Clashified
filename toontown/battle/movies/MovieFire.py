from direct.interval.IntervalGlobal import *
from toontown.battle.BattleBase import *
from toontown.battle.movies.BattleProps import *
from toontown.battle.movies.BattleSounds import *
from toontown.toon.ToonDNA import *
from toontown.suit.SuitDNA import *
from direct.directnotify import DirectNotifyGlobal
import MovieCamera
import MovieUtil

notify = DirectNotifyGlobal.directNotify.newCategory('MovieThrow')
hitSoundFiles = ('AA_tart_only.ogg', 'AA_slice_only.ogg', 'AA_slice_only.ogg', 'AA_slice_only.ogg', 'AA_slice_only.ogg',
                 'AA_wholepie_only.ogg', 'AA_wholepie_only.ogg')
tPieLeavesHand = 2.7
tPieHitsSuit = 3.0
tSuitDodges = 2.45
ratioMissToHit = 1.5
tPieShrink = 0.7
pieFlyTaskName = 'MovieThrow-pieFly'


def addHit(dict, suitId, hitCount):
    if suitId in dict:
        dict[suitId] += hitCount
    else:
        dict[suitId] = hitCount


def doFires(fires):
    if len(fires) == 0:
        return (None, None)

    suitFiresDict = {}
    for fire in fires:
        suitId = fire['target']['suit'].doId
        if suitId in suitFiresDict:
            suitFiresDict[suitId].append(fire)
        else:
            suitFiresDict[suitId] = [fire]

    suitFires = MovieUtil.sortAttacks(suitFiresDict)

    totalHitDict = {}
    singleHitDict = {}
    groupHitDict = {}

    for fire in fires:
        suitId = fire['target']['suit'].doId
        if 1:
            if fire['target']['hp'] > 0:
                addHit(singleHitDict, suitId, 1)
                addHit(totalHitDict, suitId, 1)
            else:
                addHit(singleHitDict, suitId, 0)
                addHit(totalHitDict, suitId, 0)

    notify.debug('singleHitDict = %s' % singleHitDict)
    notify.debug('groupHitDict = %s' % groupHitDict)
    notify.debug('totalHitDict = %s' % totalHitDict)

    delay = 0.0
    mtrack = Parallel()
    for sf in suitFires:
        if len(sf) > 0:
            interval = __doSuitFires(sf)
            if interval:
                mtrack.append(Sequence(Wait(delay), interval))
            delay = delay + TOON_FIRE_SUIT_DELAY

    retTrack = Sequence()
    retTrack.append(mtrack)
    camDuration = retTrack.getDuration()
    camTrack = MovieCamera.chooseFireShot(fires, suitFiresDict, camDuration)
    return retTrack, camTrack


def __doSuitFires(fires):
    toonTracks = Parallel()
    delay = 0.0
    hitCount = 0
    for fire in fires:
        if fire['target']['hp'] > 0:
            hitCount += 1
        else:
            break

    suitList = []
    for fire in fires:
        if fire['target']['suit'] not in suitList:
            suitList.append(fire['target']['suit'])

    for fire in fires:
        showSuitCannon = 1
        if fire['target']['suit'] not in suitList:
            showSuitCannon = 0
        else:
            suitList.remove(fire['target']['suit'])
        tracks = __fireCog(fire, delay, hitCount, showSuitCannon)
        if tracks:
            for track in tracks:
                toonTracks.append(track)

        delay = delay + TOON_THROW_DELAY

    return toonTracks


def __getSoundTrack(level, hitSuit, node=None):
    buttonSound = globalBattleSoundCache.getSound('AA_drop_trigger_box.ogg')
    return Sequence(Wait(2.15), SoundInterval(buttonSound, node=node))


def __fireCog(throw, delay, hitCount, showCannon=1):
    toon = throw['toon']
    target = throw['target']
    suit = target['suit']
    hp = target['hp']
    died = target['died']
    level = throw['level']
    battle = throw['battle']
    suitPos = suit.getPos(battle)
    origHpr = toon.getHpr(battle)
    hitSuit = hp > 0
    toonTrack, buttonTrack = MovieUtil.createButtonInterval(battle, delay, origHpr, suitPos, toon)
    toonTrack.append(ActorInterval(toon, 'wave', duration=2.0))
    toonTrack.append(ActorInterval(toon, 'duck'))
    soundTrack = __getSoundTrack(level, hitSuit, toon)
    suitResponseTrack = Sequence()
    if showCannon:
        showDamage = Func(suit.showHpText, -hp, openEnded=0)
        updateHealthBar = Func(suit.updateHealthBar, hp)
        cannon = loader.loadModel('phase_4/models/minigames/toon_cannon')
        barrel = cannon.find('**/cannon')
        barrel.setHpr(0, 90, 0)
        cannonHolder = render.attachNewNode('CannonHolder')
        cannon.reparentTo(cannonHolder)
        cannon.setPos(0, 0, -8.6)
        cannonHolder.setPos(suit.getPos(render))
        cannonHolder.setHpr(suit.getHpr(render))
        cannonAttachPoint = barrel.attachNewNode('CannonAttach')
        kapowAttachPoint = barrel.attachNewNode('kapowAttach')
        scaleFactor = 1.6
        iScale = 1 / scaleFactor
        barrel.setScale(scaleFactor, 1, scaleFactor)
        cannonAttachPoint.setScale(iScale, 1, iScale)
        cannonAttachPoint.setPos(0, 6.7, 0)
        kapowAttachPoint.setPos(0, -0.5, 1.9)
        suit.reparentTo(cannonAttachPoint)
        suit.setPos(0, 0, 0)
        suit.setHpr(0, -90, 0)
        suitLevel = suit.getActualLevel()
        deep = 2.5 + suitLevel * 0.2
        import math
        suitScale = 0.9 - math.sqrt(suitLevel) * 0.1
        posInit = cannonHolder.getPos()
        posFinal = Point3(posInit[0] + 0.0, posInit[1] + 0.0, posInit[2] + 7.0)
        kapow = globalPropPool.getProp('kapow')
        kapow.reparentTo(kapowAttachPoint)
        kapow.hide()
        kapow.setScale(0.25)
        kapow.setBillboardPointEye()
        smoke = loader.loadModel('phase_4/models/props/test_clouds')
        smoke.reparentTo(cannonAttachPoint)
        smoke.setScale(0.5)
        smoke.hide()
        smoke.setBillboardPointEye()
        soundBomb = base.loader.loadSfx('phase_4/audio/sfx/MG_cannon_fire_alt.ogg')
        playSoundBomb = SoundInterval(soundBomb, node=cannonHolder)
        soundFly = base.loader.loadSfx('phase_4/audio/sfx/firework_whistle_01.ogg')
        playSoundFly = SoundInterval(soundFly, node=cannonHolder)
        soundCannonAdjust = base.loader.loadSfx('phase_4/audio/sfx/MG_cannon_adjust.ogg')
        playSoundCannonAdjust = SoundInterval(soundCannonAdjust, duration=0.6, node=cannonHolder)
        soundCogPanic = base.loader.loadSfx('phase_5/audio/sfx/ENC_cogafssm.ogg')
        playSoundCogPanic = SoundInterval(soundCogPanic, node=cannonHolder)
        reactIval = Parallel(ActorInterval(suit, 'pie-small-react'),
                             Sequence(Wait(0.0),
                                      LerpPosInterval(cannonHolder, 2.0, posFinal,
                                                      startPos=posInit, blendType='easeInOut'),
                                      Parallel(LerpHprInterval(barrel, 0.6, Point3(0, 45, 0),
                                                               startHpr=Point3(0, 90, 0), blendType='easeIn'),
                                               playSoundCannonAdjust),
                                      Wait(2.0),
                                      Parallel(LerpHprInterval(barrel, 0.6, Point3(0, 90, 0),
                                                               startHpr=Point3(0, 45, 0), blendType='easeIn'),
                                               playSoundCannonAdjust),
                                      LerpPosInterval(cannonHolder, 1.0, posInit,
                                                      startPos=posFinal, blendType='easeInOut')),
                             Sequence(Wait(0.0),
                                      Parallel(ActorInterval(suit, 'flail'),
                                               suit.scaleInterval(1.0, suitScale),
                                               LerpPosInterval(suit, 0.25, Point3(0, -1.0, 0.0)),
                                               Sequence(Wait(0.25),
                                                        Parallel(playSoundCogPanic,
                                                                 LerpPosInterval(suit, 1.5, Point3(0, -deep, 0.0),
                                                                                 blendType='easeIn')))),
                                      Wait(2.5),
                                      Parallel(playSoundBomb,
                                               playSoundFly,
                                               Sequence(Func(smoke.show),
                                                        Parallel(LerpScaleInterval(smoke, 0.5, 3),
                                                                 LerpColorScaleInterval(smoke, 0.5, Vec4(2, 2, 2, 0))),
                                                        Func(smoke.hide)),
                                               Sequence(Func(kapow.show), ActorInterval(kapow, 'kapow'),
                                                        Func(kapow.hide)),
                                               LerpPosInterval(suit, 3.0, Point3(0, 150.0, 0.0)),
                                               suit.scaleInterval(3.0, 0.01)), Func(suit.hide)))
        if hitCount == 1:
            suitInterval = Sequence(Parallel(reactIval, MovieUtil.createSuitStunInterval(suit, 0.3, 1.3)), Wait(0.0),
                                    Func(cannonHolder.remove))
        else:
            suitInterval = reactIval
        suitResponseTrack.append(Wait(delay + tPieHitsSuit))
        suitResponseTrack.append(showDamage)
        suitResponseTrack.append(updateHealthBar)
        suitResponseTrack.append(suitInterval)
    return [toonTrack,
            soundTrack,
            buttonTrack,
            suitResponseTrack]