from libotp import *
from direct.interval.IntervalGlobal import *
from toontown.battle.movies.BattleProps import *
from toontown.suit.SuitDNA import *
from toontown.battle.BattleBase import *
from toontown.battle.movies.BattleSounds import *
import MovieCamera
from direct.directnotify import DirectNotifyGlobal
import MovieUtil
import toontown.battle.movies.BattleParticles
from toontown.toonbase import ToontownGlobals
from toontown.toonbase import TTLocalizer

notify = DirectNotifyGlobal.directNotify.newCategory('MovieSuitCheats')


def __doDamage(toon, dmg, died):
    if dmg > 0 and toon.hp:
        toon.takeDamage(dmg)
    return


def __showProp(prop, parent, pos, hpr=None, scale=None):
    prop.reparentTo(parent)
    prop.setPos(pos)
    if hpr:
        prop.setHpr(hpr)
    if scale:
        prop.setScale(scale)


def __animProp(prop, propName, propType='actor'):
    if 'actor' == propType:
        prop.play(propName)
    elif 'model' == propType:
        pass
    else:
        self.notify.error('No such propType as: %s' % propType)


def __suitFacePoint(suit, zOffset=0):
    pnt = suit.getPos()
    pnt.setZ(pnt[2] + suit.shoulderHeight + 0.3 + zOffset)
    return Point3(pnt)


def __toonFacePoint(toon, zOffset=0, parent=render):
    pnt = toon.getPos(parent)
    pnt.setZ(pnt[2] + toon.shoulderHeight + 0.3 + zOffset)
    return Point3(pnt)


def __toonTorsoPoint(toon, zOffset=0):
    pnt = toon.getPos()
    pnt.setZ(pnt[2] + toon.shoulderHeight - 0.2)
    return Point3(pnt)


def __throwBounceHitPoint(prop, toon):
    startPoint = prop.getPos()
    endPoint = __toonFacePoint(toon)
    return __throwBouncePoint(startPoint, endPoint)


def __throwBouncePoint(startPoint, endPoint):
    midPoint = startPoint + (endPoint - startPoint) / 2.0
    midPoint.setZ(0)
    return Point3(midPoint)


def doSuitCheat(cheat):
    notify.debug('building suit attack in doSuitAttack: %s' % cheat['name'])
    name = cheat['id']
    if name == WORKERS_COMPENSATION:
        suitTrack = doWorkersCompensation(cheat)
    else:
        notify.warning('unimplemented cheat %s!' % name)
        return None, None
    camTrack = MovieCamera.chooseSuitShot(cheat, suitTrack.getDuration())
    battle = cheat['battle']
    target = cheat['target']
    groupStatus = cheat['group']
    if groupStatus == ATK_TGT_SINGLE:
        toon = target['toon']
        toonHprTrack = Sequence(Func(toon.headsUp, battle, MovieUtil.PNT3_ZERO), Func(toon.loop, 'neutral'))
    else:
        toonHprTrack = Parallel()
        for t in target:
            toon = t['toon']
            toonHprTrack.append(Sequence(Func(toon.headsUp, battle, MovieUtil.PNT3_ZERO), Func(toon.loop, 'neutral')))

    suit = cheat['suit']
    neutralIval = Func(suit.doNeutralAnim)
    suitTrack = Sequence(suitTrack, neutralIval, toonHprTrack)
    return suitTrack, camTrack


def exitLure(attack):
    battle = attack['battle']
    suit = attack['suit']
    resetTrack = getResetTrack(suit, battle)
    suitTrack = Sequence(resetTrack)
    waitTrack = Sequence(Wait(resetTrack.getDuration()), Func(battle.unlureSuit, suit))
    camTrack = Sequence(waitTrack)
    return suitTrack, camTrack


def getResetTrack(suit, battle):
    resetPos, resetHpr = battle.getActorPosHpr(suit)
    moveDist = Vec3(suit.getPos(battle) - resetPos).length()
    moveDuration = 0.5
    walkTrack = Sequence(Func(suit.setHpr, battle, resetHpr),
                         ActorInterval(suit, 'walk', startTime=1, duration=moveDuration, endTime=1e-05),
                         Func(suit.doNeutralAnim))
    moveTrack = LerpPosInterval(suit, moveDuration, resetPos, other=battle)
    return Parallel(walkTrack, moveTrack)


def __makeCancelledNodePath():
    tn = TextNode('CANCELLED')
    tn.setFont(getSuitFont())
    tn.setText(TTLocalizer.MovieSuitCancelled)
    tn.setAlign(TextNode.ACenter)
    tntop = hidden.attachNewNode('CancelledTop')
    tnpath = tntop.attachNewNode(tn)
    tnpath.setPosHpr(0, 0, 0, 0, 0, 0)
    tnpath.setScale(1)
    tnpath.setColor(0.7, 0, 0, 1)
    tnpathback = tnpath.instanceUnderNode(tntop, 'backside')
    tnpathback.setPosHpr(0, 0, 0, 180, 0, 0)
    tnpath.setScale(1)
    return tntop


def getSuitTrack(cheat, delay=1e-06, splicedAnims=None):
    suit = cheat['suit']
    battle = cheat['battle']
    tauntIndex = cheat['taunt']
    target = cheat['target']
    targetPos = None
    if 'toon' in target:
        toon = target['toon']
        targetPos = toon.getPos(battle)
    taunt = getCheatTaunt(cheat['name'], tauntIndex)
    track = Sequence(Wait(delay), Func(suit.setChatAbsolute, taunt, CFSpeech | CFTimeout))

    if targetPos:
        track.append(Func(suit.headsUp, battle, targetPos))
    if splicedAnims:
        track.append(getSplicedAnimsTrack(splicedAnims, actor=suit))
    else:
        track.append(ActorInterval(suit, cheat['animName']))
    origPos, origHpr = battle.getActorPosHpr(suit)
    track.append(Func(suit.setHpr, battle, origHpr))

    track.append(Func(suit.clearChat))
    return track


def getSuitAnimTrack(attack, delay=0):
    suit = attack['suit']
    tauntIndex = attack['taunt']
    taunt = getAttackTaunt(attack['name'], tauntIndex)
    return Sequence(Wait(delay), Func(suit.setChatAbsolute, taunt, CFSpeech | CFTimeout),
                    ActorInterval(attack['suit'], attack['animName']), Func(suit.clearChat))


def getPartTrack(particleEffect, startDelay, durationDelay, partExtraArgs):
    particleEffect = partExtraArgs[0]
    parent = partExtraArgs[1]
    if len(partExtraArgs) > 2:
        worldRelative = partExtraArgs[2]
    else:
        worldRelative = 1
    return Sequence(Wait(startDelay),
                    ParticleInterval(particleEffect, parent, worldRelative, duration=durationDelay, cleanup=True))


def getToonTrack(attack, damageDelay=1e-06, damageAnimNames=None, dodgeDelay=0.0001, dodgeAnimNames=None,
                 splicedDamageAnims=None, splicedDodgeAnims=None, target=None, showDamageExtraTime=0.01,
                 showMissedExtraTime=0.5):
    if not target:
        target = attack['target']
    toon = target['toon']
    battle = attack['battle']
    suit = attack['suit']
    suitPos = suit.getPos(battle)
    dmg = target['hp']
    animTrack = Sequence()
    animTrack.append(Func(toon.headsUp, battle, suitPos))
    if dmg > 0:
        animTrack.append(
            getToonTakeDamageTrack(toon, target['died'], dmg, damageDelay, damageAnimNames, splicedDamageAnims,
                                   showDamageExtraTime))
        return animTrack
    else:
        animTrack.append(getToonDodgeTrack(target, dodgeDelay, dodgeAnimNames, splicedDodgeAnims, showMissedExtraTime))
        indicatorTrack = Sequence(Wait(dodgeDelay + showMissedExtraTime), Func(MovieUtil.indicateMissed, toon))
        return Parallel(animTrack, indicatorTrack)


def getToonTracks(attack, damageDelay=1e-06, damageAnimNames=None, dodgeDelay=1e-06, dodgeAnimNames=None,
                  splicedDamageAnims=None, splicedDodgeAnims=None, showDamageExtraTime=0.01, showMissedExtraTime=0.5):
    toonTracks = Parallel()
    targets = attack['target']
    for i in xrange(len(targets)):
        tgt = targets[i]
        toonTracks.append(
            getToonTrack(attack, damageDelay, damageAnimNames, dodgeDelay, dodgeAnimNames, splicedDamageAnims,
                         splicedDodgeAnims, target=tgt, showDamageExtraTime=showDamageExtraTime,
                         showMissedExtraTime=showMissedExtraTime))

    return toonTracks


def getToonDodgeTrack(target, dodgeDelay, dodgeAnimNames, splicedDodgeAnims, showMissedExtraTime):
    toon = target['toon']
    toonTrack = Sequence()
    toonTrack.append(Wait(dodgeDelay))
    if dodgeAnimNames:
        for d in dodgeAnimNames:
            if d == 'sidestep':
                toonTrack.append(getAllyToonsDodgeParallel(target))
            else:
                toonTrack.append(ActorInterval(toon, d))

    else:
        toonTrack.append(getSplicedAnimsTrack(splicedDodgeAnims, actor=toon))
    toonTrack.append(Func(toon.loop, 'neutral'))
    return toonTrack


def getAllyToonsDodgeParallel(target):
    toon = target['toon']
    leftToons = target['leftToons']
    rightToons = target['rightToons']
    if len(leftToons) > len(rightToons):
        PoLR = rightToons
        PoMR = leftToons
    else:
        PoLR = leftToons
        PoMR = rightToons
    upper = 1 + 4 * abs(len(leftToons) - len(rightToons))
    if random.randint(0, upper) > 0:
        toonDodgeList = PoLR
    else:
        toonDodgeList = PoMR
    if toonDodgeList is leftToons:
        sidestepAnim = 'sidestep-left'
        soundEffect = globalBattleSoundCache.getSound('AV_side_step.ogg')
    else:
        sidestepAnim = 'sidestep-right'
        soundEffect = globalBattleSoundCache.getSound('AV_jump_to_side.ogg')
    toonTracks = Parallel()
    for t in toonDodgeList:
        toonTracks.append(Sequence(ActorInterval(t, sidestepAnim), Func(t.loop, 'neutral')))

    toonTracks.append(Sequence(ActorInterval(toon, sidestepAnim), Func(toon.loop, 'neutral')))
    toonTracks.append(Sequence(Wait(0.5), SoundInterval(soundEffect, node=toon)))
    return toonTracks


def getPropTrack(prop, parent, posPoints, appearDelay, remainDelay, scaleUpPoint=Point3(1), scaleUpTime=0.5,
                 scaleDownTime=0.5, startScale=Point3(0.01), anim=0, propName='none', animDuration=0.0,
                 animStartTime=0.0):
    if anim == 1:
        track = Sequence(Wait(appearDelay), Func(__showProp, prop, parent, *posPoints),
                         LerpScaleInterval(prop, scaleUpTime, scaleUpPoint, startScale=startScale),
                         ActorInterval(prop, propName, duration=animDuration, startTime=animStartTime),
                         Wait(remainDelay), Func(MovieUtil.removeProp, prop))
    else:
        track = Sequence(Wait(appearDelay), Func(__showProp, prop, parent, *posPoints),
                         LerpScaleInterval(prop, scaleUpTime, scaleUpPoint, startScale=startScale), Wait(remainDelay),
                         LerpScaleInterval(prop, scaleDownTime, MovieUtil.PNT3_NEARZERO),
                         Func(MovieUtil.removeProp, prop))
    return track


def getPropAppearTrack(prop, parent, posPoints, appearDelay, scaleUpPoint=Point3(1), scaleUpTime=0.5,
                       startScale=Point3(0.01), poseExtraArgs=None):
    propTrack = Sequence(Wait(appearDelay), Func(__showProp, prop, parent, *posPoints))
    if poseExtraArgs:
        propTrack.append(Func(prop.pose, *poseExtraArgs))
    propTrack.append(LerpScaleInterval(prop, scaleUpTime, scaleUpPoint, startScale=startScale))
    return propTrack


def getPropThrowTrack(attack, prop, hitPoints=[], missPoints=[], hitDuration=0.5, missDuration=0.5,
                      hitPointNames='none', missPointNames='none', lookAt='none', groundPointOffSet=0,
                      missScaleDown=None, parent=render):
    target = attack['target']
    toon = target['toon']
    dmg = target['hp']
    battle = attack['battle']

    def getLambdas(list, prop, toon):
        for i in xrange(len(list)):
            if list[i] == 'face':
                list[i] = lambda toon=toon: __toonFacePoint(toon)
            elif list[i] == 'miss':
                list[i] = lambda prop=prop, toon=toon: __toonMissPoint(prop, toon)
            elif list[i] == 'bounceHit':
                list[i] = lambda prop=prop, toon=toon: __throwBounceHitPoint(prop, toon)
            elif list[i] == 'bounceMiss':
                list[i] = lambda prop=prop, toon=toon: __throwBounceMissPoint(prop, toon)

        return list

    if hitPointNames != 'none':
        hitPoints = getLambdas(hitPointNames, prop, toon)
    if missPointNames != 'none':
        missPoints = getLambdas(missPointNames, prop, toon)
    propTrack = Sequence()
    propTrack.append(Func(battle.movie.needRestoreRenderProp, prop))
    propTrack.append(Func(prop.wrtReparentTo, parent))
    if lookAt != 'none':
        propTrack.append(Func(prop.lookAt, lookAt))
    if dmg > 0:
        for i in xrange(len(hitPoints)):
            pos = hitPoints[i]
            propTrack.append(LerpPosInterval(prop, hitDuration, pos=pos))

    else:
        for i in xrange(len(missPoints)):
            pos = missPoints[i]
            propTrack.append(LerpPosInterval(prop, missDuration, pos=pos))

        if missScaleDown:
            propTrack.append(LerpScaleInterval(prop, missScaleDown, MovieUtil.PNT3_NEARZERO))
    propTrack.append(Func(MovieUtil.removeProp, prop))
    propTrack.append(Func(battle.movie.clearRenderProp, prop))
    return propTrack


def getThrowTrack(object, target, duration=1.0, parent=render, gravity=-32.144):
    values = {}

    def calcOriginAndVelocity(object=object, target=target, values=values, duration=duration, parent=parent,
                              gravity=gravity):
        if callable(target):
            target = target()
        object.wrtReparentTo(parent)
        values['origin'] = object.getPos(parent)
        origin = object.getPos(parent)
        values['velocity'] = (target[2] - origin[2] - 0.5 * gravity * duration * duration) / duration

    return Sequence(Func(calcOriginAndVelocity),
                    LerpFunctionInterval(throwPos, fromData=0.0, toData=1.0, duration=duration, extraArgs=[object,
                                                                                                           duration,
                                                                                                           target,
                                                                                                           values,
                                                                                                           gravity]))


def throwPos(t, object, duration, target, values, gravity=-32.144):
    origin = values['origin']
    velocity = values['velocity']
    if callable(target):
        target = target()
    x = origin[0] * (1 - t) + target[0] * t
    y = origin[1] * (1 - t) + target[1] * t
    time = t * duration
    z = origin[2] + velocity * time + 0.5 * gravity * time * time
    object.setPos(x, y, z)


def getToonTakeDamageTrack(toon, died, dmg, delay, damageAnimNames=None, splicedDamageAnims=None,
                           showDamageExtraTime=0.01):
    toonTrack = Sequence()
    toonTrack.append(Wait(delay))
    if damageAnimNames:
        for d in damageAnimNames:
            toonTrack.append(ActorInterval(toon, d))

        indicatorTrack = Sequence(Wait(delay + showDamageExtraTime), Func(__doDamage, toon, dmg, died))
    else:
        splicedAnims = getSplicedAnimsTrack(splicedDamageAnims, actor=toon)
        toonTrack.append(splicedAnims)
        indicatorTrack = Sequence(Wait(delay + showDamageExtraTime), Func(__doDamage, toon, dmg, died))
    toonTrack.append(Func(toon.loop, 'neutral'))
    if died:
        toonTrack.append(Wait(5.0))
    return Parallel(toonTrack, indicatorTrack)


def getSplicedAnimsTrack(anims, actor=None):
    track = Sequence()
    for nextAnim in anims:
        delay = 1e-06
        if len(nextAnim) >= 2:
            if nextAnim[1] > 0:
                delay = nextAnim[1]
        if len(nextAnim) <= 0:
            track.append(Wait(delay))
        elif len(nextAnim) == 1:
            track.append(ActorInterval(actor, nextAnim[0]))
        elif len(nextAnim) == 2:
            track.append(Wait(delay))
            track.append(ActorInterval(actor, nextAnim[0]))
        elif len(nextAnim) == 3:
            track.append(Wait(delay))
            track.append(ActorInterval(actor, nextAnim[0], startTime=nextAnim[2]))
        elif len(nextAnim) == 4:
            track.append(Wait(delay))
            duration = nextAnim[3]
            if duration < 0:
                startTime = nextAnim[2]
                endTime = startTime + duration
                if endTime <= 0:
                    endTime = 0.01
                track.append(ActorInterval(actor, nextAnim[0], startTime=startTime, endTime=endTime))
            else:
                track.append(ActorInterval(actor, nextAnim[0], startTime=nextAnim[2], duration=duration))
        elif len(nextAnim) == 5:
            track.append(Wait(delay))
            track.append(ActorInterval(nextAnim[4], nextAnim[0], startTime=nextAnim[2], duration=nextAnim[3]))

    return track


def getSplicedLerpAnims(animName, origDuration, newDuration, startTime=0, fps=30, reverse=0):
    anims = []
    addition = 0
    numAnims = origDuration * fps
    timeInterval = newDuration / numAnims
    animInterval = origDuration / numAnims
    if reverse == 1:
        animInterval = -animInterval
    for i in xrange(0, int(numAnims)):
        anims.append([animName,
                      timeInterval,
                      startTime + addition,
                      animInterval])
        addition += animInterval

    return anims


def getSoundTrack(fileName, delay=0.01, duration=None, node=None):
    soundEffect = globalBattleSoundCache.getSound(fileName)
    if duration:
        return Sequence(Wait(delay), SoundInterval(soundEffect, duration=duration, node=node))
    else:
        return Sequence(Wait(delay), SoundInterval(soundEffect, node=node))


def doWorkersCompensation(attack):
    suit = attack['suit']
    hp = attack['target']['hp']
    suitTrack = getSuitTrack(attack)
    soundTrack = getSoundTrack('SA_finger_wag.ogg', delay=1.3, node=suit)
    healTrack = Sequence(Wait(2.7), Func(suit.showHpText, hp, openEnded=0), Func(suit.updateHealthBar, -hp))
    return Parallel(suitTrack, soundTrack, healTrack)
