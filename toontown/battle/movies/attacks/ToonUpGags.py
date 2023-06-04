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
from toontown.battle.movies.attacks.ToonUpMovieFunctionality import *

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

notify = DirectNotifyGlobal.directNotify.newCategory('ToonUpGags')

def Feather(heal):
    toon = heal['toon']
    target = heal['target'][0]
    targetToon = target['toon']
    hp = target['hp']
    ineffective = heal['sidestep']
    level = heal['level']
    track = Sequence(runToHealSpot(heal))
    feather1 = globalPropPool.getProp('feather')
    feather2 = MovieUtil.copyProp(feather1)
    feathers = [feather1, feather2]
    hands = toon.getRightHands()

    def scaleFeathers():
        toon.pose('tickle', 63)
        toon.update(0)
        hand = toon.getRightHands()[0]
        horizDistance = Vec3(hand.getPos(render) - target.getPos(render))
        horizDistance.setZ(0)
        distance = horizDistance.length()
        if target.style.torso[0] == 's':
            distance -= 0.5
        else:
            distance -= 0.3
        featherLen = 2.4
        scale = distance / (featherLen * hand.getScale(render)[0])
        for feather in feathers:
            feather.setScale(scale)

    tFeatherScaleUp = 0.5
    dFeatherScaleUp = 0.5
    dFeatherScaleDown = 0.5
    featherTrack = Parallel(MovieUtil.getActorIntervals(feathers, 'feather'),
                            Sequence(Wait(tFeatherScaleUp),
                                     Func(MovieUtil.showProps, feathers, hands),
                                     Func(scaleFeathers, feathers),
                                     MovieUtil.getScaleIntervals(feathers, dFeatherScaleUp,
                                                                 MovieUtil.PNT3_NEARZERO, feathers[0].getScale)),
                            Sequence(Wait(toon.getDuration('tickle') - dFeatherScaleDown),
                                     MovieUtil.getScaleIntervals(feathers, dFeatherScaleDown, None,
                                                                 MovieUtil.PNT3_NEARZERO)))
    tHeal = 3.0
    mtrack = Parallel(featherTrack, ActorInterval(toon, 'tickle'),
                      getSoundTrack(level, 1, node=toon),
                      Sequence(Wait(tHeal), Func(healToon, targetToon, hp, ineffective),
                               ActorInterval(targetToon, 'cringe', startTime=20.0 / targetToon.getFrameRate('cringe'))))
    track.append(mtrack)
    track.append(Func(MovieUtil.removeProps, feathers))
    track.append(returnToBase(heal))
    track.append(Func(targetToon.clearChat))
    return track

def Megaphone(heal):
    npcId = 0
    if 'npcId' in heal:
        npcId = heal['npcId']
        toon = NPCToons.createLocalNPC(npcId)
        if toon is None:
            return
    else:
        toon = heal['toon']
    targets = heal['target']
    ineffective = heal['sidestep']
    level = heal['level']
    jokeIndex = heal['hpBonus'][0] % len(toonHealJokes)
    if npcId != 0:
        track = Sequence(MovieNPCSOS.teleportIn(heal, toon))
    else:
        track = Sequence(runToHealSpot(heal))
    tracks = Parallel()
    fSpeakPunchline = 58
    tSpeakSetup = 0.0
    tSpeakPunchline = 3.0
    dPunchLine = 3.0
    tTargetReact = tSpeakPunchline + 1.0
    dTargetLaugh = 1.5
    tRunBack = tSpeakPunchline + dPunchLine
    tDoSoundAnimation = tSpeakPunchline - float(fSpeakPunchline) / toon.getFrameRate('sound')
    megaphone = globalPropPool.getProp('megaphone')
    megaphone2 = MovieUtil.copyProp(megaphone)
    megaphones = [megaphone, megaphone2]
    hands = toon.getRightHands()
    dMegaphoneScale = 0.5
    tracks.append(Sequence(Wait(tDoSoundAnimation),
                           Func(MovieUtil.showProps, megaphones, hands),
                           MovieUtil.getScaleIntervals(megaphones, dMegaphoneScale, MovieUtil.PNT3_NEARZERO,
                                                       MovieUtil.PNT3_ONE),
                           Wait(toon.getDuration('sound') - 2.0 * dMegaphoneScale),
                           MovieUtil.getScaleIntervals(megaphones, dMegaphoneScale, MovieUtil.PNT3_ONE,
                                                       MovieUtil.PNT3_NEARZERO),
                           Func(MovieUtil.removeProps, megaphones)))
    tracks.append(Sequence(Wait(tDoSoundAnimation), ActorInterval(toon, 'sound')))
    soundTrack = getSoundTrack(level, 2.0, node=toon)
    tracks.append(soundTrack)
    joke = toonHealJokes[jokeIndex]
    tracks.append(Sequence(Wait(tSpeakSetup), Func(toon.setChatAbsolute, joke[0], CFSpeech | CFTimeout)))
    tracks.append(Sequence(Wait(tSpeakPunchline), Func(toon.setChatAbsolute, joke[1], CFSpeech | CFTimeout)))
    reactTrack = Sequence(Wait(tTargetReact))
    for target in targets:
        targetToon = target['toon']
        hp = target['hp']
        reactTrack.append(Func(healToon, targetToon, hp, ineffective))

    reactTrack.append(Wait(dTargetLaugh))
    for target in targets:
        targetToon = target['toon']
        reactTrack.append(Func(targetToon.clearChat))

    tracks.append(reactTrack)
    if npcId != 0:
        track.append(Sequence(Wait(tRunBack), Func(toon.clearChat), *MovieNPCSOS.teleportOut(heal, toon)))
    else:
        tracks.append(Sequence(Wait(tRunBack), Func(toon.clearChat), *returnToBase(heal)))
    track.append(tracks)
    return track

def Lipstick(heal):
    toon = heal['toon']
    target = heal['target'][0]
    targetToon = target['toon']
    hp = target['hp']
    level = heal['level']
    ineffective = heal['sidestep']
    track = Sequence(runToHealSpot(heal))
    lipstick = globalPropPool.getProp('lipstick')
    lipstick2 = MovieUtil.copyProp(lipstick)
    lipsticks = [lipstick, lipstick2]
    rightHands = toon.getRightHands()
    dScale = 0.5
    lipstickTrack = Sequence(
        Func(MovieUtil.showProps, lipsticks, rightHands, Point3(-0.27, -0.24, -0.95), Point3(-118, -10.6, -25.9)),
        MovieUtil.getScaleIntervals(lipsticks, dScale, MovieUtil.PNT3_NEARZERO, MovieUtil.PNT3_ONE),
        Wait(toon.getDuration('smooch') - 2.0 * dScale),
        MovieUtil.getScaleIntervals(lipsticks, dScale, MovieUtil.PNT3_ONE, MovieUtil.PNT3_NEARZERO),
        Func(MovieUtil.removeProps, lipsticks))
    lips = globalPropPool.getProp('lips')
    dScale = 0.5
    tLips = 2.5
    tThrow = 115.0 / toon.getFrameRate('smooch')
    dThrow = 0.5

    def getLipPos(toon=toon):
        toon.pose('smooch', 57)
        toon.update(0)
        hand = toon.getRightHands()[0]
        return hand.getPos(render)

    lipsTrack = Sequence(Wait(tLips), Func(MovieUtil.showProp, lips, render, getLipPos),
                         Func(lips.setBillboardPointWorld),
                         LerpScaleInterval(lips, dScale, Point3(3, 3, 3), startScale=MovieUtil.PNT3_NEARZERO),
                         Wait(tThrow - tLips - dScale), LerpPosInterval(lips, dThrow, Point3(
            targetToon.getPos() + Point3(0, 0, targetToon.getHeight()))), Func(
            MovieUtil.removeProp, lips))
    delay = tThrow + dThrow
    mtrack = Parallel(lipstickTrack, lipsTrack, getSoundTrack(level, 2, node=toon),
                      Sequence(ActorInterval(toon, 'smooch'), *returnToBase(heal)),
                      Sequence(Wait(delay), ActorInterval(targetToon, 'conked')),
                      Sequence(Wait(delay), Func(healToon, targetToon, hp, ineffective)))
    track.append(mtrack)
    track.append(Func(targetToon.clearChat))
    return track

def BambooCane(heal):
    npcId = 0
    if 'npcId' in heal:
        npcId = heal['npcId']
        toon = NPCToons.createLocalNPC(npcId)
        if toon is None:
            return
    else:
        toon = heal['toon']
    targets = heal['target']
    ineffective = heal['sidestep']
    level = heal['level']
    if npcId != 0:
        track = Sequence(MovieNPCSOS.teleportIn(heal, toon))
    else:
        track = Sequence(runToHealSpot(heal))
    delay = 3.0
    first = 1
    targetTrack = Sequence()
    for target in targets:
        targetToon = target['toon']
        hp = target['hp']
        reactIval = Func(healToon, targetToon, hp, ineffective)
        if first:
            targetTrack.append(Wait(delay))
            first = 0
        targetTrack.append(reactIval)

    hat = globalPropPool.getProp('hat')
    hat2 = MovieUtil.copyProp(hat)
    hats = [hat, hat2]
    cane = globalPropPool.getProp('cane')
    cane2 = MovieUtil.copyProp(cane)
    canes = [cane, cane2]
    leftHands = toon.getLeftHands()
    rightHands = toon.getRightHands()
    dScale = 0.5
    propTrack = Sequence(Func(MovieUtil.showProps, hats, rightHands, Point3(0.23, 0.09, 0.69), Point3(180, 0, 0)), Func(
        MovieUtil.showProps, canes, leftHands, Point3(-0.28, 0.0, 0.14), Point3(0.0, 0.0, -150.0)),
                         MovieUtil.getScaleIntervals(hats + canes, dScale, MovieUtil.PNT3_NEARZERO, MovieUtil.PNT3_ONE),
                         Wait(toon.getDuration('happy-dance') - 2.0 * dScale),
                         MovieUtil.getScaleIntervals(hats + canes, dScale, MovieUtil.PNT3_ONE, MovieUtil.PNT3_NEARZERO),
                         Func(
                             MovieUtil.removeProps, hats + canes))
    mtrack = Parallel(propTrack, ActorInterval(toon, 'happy-dance'),
                      getSoundTrack(level, 0.2, duration=6.4, node=toon), targetTrack)
    track.append(Func(toon.loop, 'neutral'))
    track.append(Wait(0.1))
    track.append(mtrack)
    if npcId != 0:
        track.append(MovieNPCSOS.teleportOut(heal, toon))
    else:
        track.append(returnToBase(heal))
    for target in targets:
        targetToon = target['toon']
        track.append(Func(targetToon.clearChat))

    return track

def PixieDust(heal):
    toon = heal['toon']
    target = heal['target'][0]
    targetToon = target['toon']
    hp = target['hp']
    ineffective = heal['sidestep']
    level = heal['level']
    track = Sequence(runToHealSpot(heal))
    sprayEffect = toontown.battle.movies.BattleParticles.createParticleEffect(file='pixieSpray')
    dropEffect = toontown.battle.movies.BattleParticles.createParticleEffect(file='pixieDrop')
    explodeEffect = toontown.battle.movies.BattleParticles.createParticleEffect(file='pixieExplode')
    poofEffect = toontown.battle.movies.BattleParticles.createParticleEffect(file='pixiePoof')
    wallEffect = toontown.battle.movies.BattleParticles.createParticleEffect(file='pixieWall')

    def face90():
        vec = Point3(targetToon.getPos() - toon.getPos())
        vec.setZ(0)
        temp = vec[0]
        vec.setX(-vec[1])
        vec.setY(temp)
        targetPoint = Point3(toon.getPos() + vec)
        toon.headsUp(render, targetPoint)

    delay = 2.5
    mtrack = Parallel(getPartTrack(sprayEffect, 1.5, 0.5, [sprayEffect, toon, 0]),
                      getPartTrack(dropEffect, 1.9, 2.0, [dropEffect, targetToon, 0]),
                      getPartTrack(explodeEffect, 2.7, 1.0, [explodeEffect, toon, 0]),
                      getPartTrack(poofEffect, 3.4, 1.0, [poofEffect, targetToon, 0]),
                      getPartTrack(wallEffect, 4.05, 1.2, [wallEffect, toon, 0]),
                      getSoundTrack(level, 2, duration=4.1, node=toon),
                      Sequence(Func(face90), ActorInterval(toon, 'sprinkle-dust')),
                      Sequence(Wait(delay), Func(healToon, targetToon, hp, ineffective)))
    track.append(mtrack)
    track.append(returnToBase(heal))
    track.append(Func(targetToon.clearChat))
    return track

def JugglingCubes(heal):
    npcId = 0
    if 'npcId' in heal:
        npcId = heal['npcId']
        toon = NPCToons.createLocalNPC(npcId)
        if toon is None:
            return
    else:
        toon = heal['toon']
    targets = heal['target']
    ineffective = heal['sidestep']
    level = heal['level']
    if npcId != 0:
        track = Sequence(MovieNPCSOS.teleportIn(heal, toon))
    else:
        track = Sequence(runToHealSpot(heal))
    delay = 4.0
    first = 1
    targetTrack = Sequence()
    for target in targets:
        targetToon = target['toon']
        hp = target['hp']
        reactIval = Func(healToon, targetToon, hp, ineffective)
        if first == 1:
            targetTrack.append(Wait(delay))
            first = 0
        targetTrack.append(reactIval)

    cube = globalPropPool.getProp('cubes')
    cube2 = MovieUtil.copyProp(cube)
    cubes = [cube, cube2]
    hips = [toon.getLOD(toon.getLODNames()[0]).find('**/joint_hips'),
            toon.getLOD(toon.getLODNames()[1]).find('**/joint_hips')]
    cubeTrack = Sequence(Func(MovieUtil.showProps, cubes, hips), MovieUtil.getActorIntervals(cubes, 'cubes'), Func(
        MovieUtil.removeProps, cubes))
    mtrack = Parallel(cubeTrack, getSoundTrack(level, 0.7, duration=7.7, node=toon), ActorInterval(toon, 'juggle'),
                      targetTrack)
    track.append(mtrack)
    if npcId != 0:
        track.append(MovieNPCSOS.teleportOut(heal, toon))
    else:
        track.append(returnToBase(heal))
    for target in targets:
        targetToon = target['toon']
        track.append(Func(targetToon.clearChat))

    return track

def HighDive(heal):
    splash = Splash.Splash(render)
    splash.reparentTo(render)
    npcId = 0
    if 'npcId' in heal:
        npcId = heal['npcId']
        toon = NPCToons.createLocalNPC(npcId)
        if toon is None:
            return
    else:
        toon = heal['toon']
    targets = heal['target']
    ineffective = heal['sidestep']
    level = heal['level']
    if npcId != 0:
        track = Sequence(MovieNPCSOS.teleportIn(heal, toon))
    else:
        track = Sequence(runToHealSpot(heal))
    delay = 7.0
    first = 1
    targetTrack = Sequence()
    for target in targets:
        targetToon = target['toon']
        hp = target['hp']
        reactIval = Func(healToon, targetToon, hp, ineffective)
        if first == 1:
            targetTrack.append(Wait(delay))
            first = 0
        targetTrack.append(reactIval)

    thisBattle = heal['battle']
    toonsInBattle = thisBattle.toons
    glass = globalPropPool.getProp('glass')
    glass.setScale(4.0)
    glass.setHpr(0.0, 90.0, 0.0)
    ladder = globalPropPool.getProp('ladder')
    placeNode = NodePath('lookNode')
    diveProps = [glass, ladder]
    ladderScale = toon.getBodyScale() / 0.66
    scaleUpPoint = Point3(0.5, 0.5, 0.45) * ladderScale
    basePos = toon.getPos()
    glassOffset = Point3(0, 1.1, 0.2)
    glassToonOffset = Point3(0, 1.2, 0.2)
    splashOffset = Point3(0, 1.0, 0.4)
    ladderOffset = Point3(0, 4, 0)
    ladderToonSep = Point3(0, 1, 0) * ladderScale
    diveOffset = Point3(0, 0, 10)
    divePos = add3(add3(ladderOffset, diveOffset), ladderToonSep)
    ladder.setH(toon.getH())
    glassPos = render.getRelativePoint(toon, glassOffset)
    glassToonPos = render.getRelativePoint(toon, glassToonOffset)
    ladderPos = render.getRelativePoint(toon, ladderOffset)
    climbladderPos = render.getRelativePoint(toon, add3(ladderOffset, ladderToonSep))
    divePos = render.getRelativePoint(toon, divePos)
    topDivePos = render.getRelativePoint(toon, diveOffset)
    lookBase = render.getRelativePoint(toon, ladderOffset)
    lookTop = render.getRelativePoint(toon, add3(ladderOffset, diveOffset))
    LookGlass = render.getRelativePoint(toon, glassOffset)
    splash.setPos(splashOffset)
    walkToLadderTime = 1.0
    climbTime = 5.0
    diveTime = 1.0
    ladderGrowTime = 1.5
    splash.setPos(glassPos)
    toonNode = toon.getGeomNode()
    placeNode.reparentTo(render)
    placeNode.setScale(5.0)
    placeNode.setPos(toon.getPos(render))
    placeNode.setHpr(toon.getHpr(render))
    toonscale = toonNode.getScale()
    toonFacing = toon.getHpr()
    propTrack = Sequence(Func(MovieUtil.showProp, glass, render, glassPos),
                         Func(MovieUtil.showProp, ladder, render, ladderPos),
                         Func(toonsLook, toonsInBattle, placeNode, Point3(0, 0, 0)), Func(placeNode.setPos, lookBase),
                         LerpScaleInterval(ladder, ladderGrowTime, scaleUpPoint, startScale=MovieUtil.PNT3_NEARZERO),
                         Func(placeNode.setPos, lookTop), Wait(2.1), MovieCamera.toonGroupHighShot(None, 0), Wait(2.1),
                         Func(placeNode.setPos, LookGlass), Wait(0.4), MovieCamera.allGroupLowShot(None, 0), Wait(1.8),
                         LerpScaleInterval(ladder, ladderGrowTime, MovieUtil.PNT3_NEARZERO, startScale=scaleUpPoint),
                         Func(
                             MovieUtil.removeProps, diveProps))
    mtrack = Parallel(propTrack, getSoundTrack(level, 0.6, duration=9.0, node=toon), Sequence(Parallel(
        Sequence(ActorInterval(toon, 'walk', loop=0, duration=walkToLadderTime),
                 ActorInterval(toon, 'neutral', loop=0, duration=0.1)),
        LerpPosInterval(toon, walkToLadderTime, climbladderPos), Wait(ladderGrowTime)), Parallel(
        ActorInterval(toon, 'climb', loop=0, endFrame=116), Sequence(Wait(4.6), Func(toonNode.setTransparency, 1),
                                                                     LerpColorScaleInterval(toonNode, 0.25,
                                                                                            VBase4(1, 1.0, 1, 0.0),
                                                                                            blendType='easeInOut'),
                                                                     LerpScaleInterval(toonNode, 0.01, 0.1,
                                                                                       startScale=toonscale),
                                                                     LerpHprInterval(toon, 0.01, toonFacing),
                                                                     LerpPosInterval(toon, 0.0, glassToonPos),
                                                                     Func(toonNode.clearTransparency),
                                                                     Func(toonNode.clearColorScale), Parallel(
                ActorInterval(toon, 'swim', loop=1, startTime=0.0, endTime=1.0), Wait(1.0))),
        Sequence(Wait(4.6), Func(splash.play), Wait(1.0), Func(splash.destroy))), Wait(0.5), Parallel(
        ActorInterval(toon, 'jump', loop=0, startTime=0.2), LerpScaleInterval(toonNode, 0.5, toonscale, startScale=0.1),
        Func(stopLook, toonsInBattle))), targetTrack)
    track.append(mtrack)
    if npcId != 0:
        track.append(MovieNPCSOS.teleportOut(heal, toon))
    else:
        track.append(returnToBase(heal))
    for target in targets:
        targetToon = target['toon']
        track.append(Func(targetToon.clearChat))

    return track