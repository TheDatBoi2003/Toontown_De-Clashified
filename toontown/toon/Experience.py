from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

from otp.otpbase import OTPGlobals
from toontown.toonbase.ToontownBattleGlobals import *


def fixTrackIndex(track):
    if type(track) is str:
        track = Tracks.index(track)
    return track


def makeFromNetString(netString):
    dataList = []
    dg = PyDatagram(netString)
    dgi = PyDatagramIterator(dg)
    for track in xrange(0, len(Tracks)):
        dataList.append(dgi.getUint16())

    return dataList


class Experience:
    notify = DirectNotifyGlobal.directNotify.newCategory('Experience')

    def __init__(self, experience=None, owner=None):
        self.owner = owner
        if experience:
            self.experience = experience
        else:
            self.experience = []
            for track in xrange(0, len(Tracks)):
                self.experience.append(StartingLevel)
        return

    def __str__(self):
        return str(self.experience)

    def makeNetString(self):
        dataList = self.experience
        datagram = PyDatagram()
        for track in xrange(0, len(Tracks)):
            datagram.addUint16(dataList[track])

        dgi = PyDatagramIterator(datagram)
        return dgi.getRemainingBytes()

    def addExp(self, track, amount=1):
        track = fixTrackIndex(track)
        self.notify.debug('adding %d exp to track %d' % (amount, track))
        if self.owner.getGameAccess() == OTPGlobals.AccessFull:
            if self.experience[track] + amount <= MaxSkill:
                self.experience[track] += amount
            else:
                self.experience[track] = MaxSkill

    def maxOutExp(self):
        for track in xrange(0, len(Tracks)):
            self.experience[track] = MaxSkill

    def makeExpRegular(self):
        import random
        for track in xrange(0, len(Tracks)):
            rank = random.choice((0, int(random.random() * 1500.0), int(random.random() * 2000.0)))
            self.experience[track] = Levels[len(Levels) - 1] - rank

    def zeroOutExp(self):
        for track in xrange(0, len(Tracks)):
            self.experience[track] = StartingLevel

    def setAllExp(self, num):
        for track in xrange(0, len(Tracks)):
            self.experience[track] = num

    def getExp(self, track):
        track = fixTrackIndex(track)
        return self.experience[track]

    def setExp(self, track, exp):
        track = fixTrackIndex(track)
        self.experience[track] = exp

    def getExpLevel(self, track):
        track = fixTrackIndex(track)
        level = 0
        for amount in Levels:
            if self.experience[track] >= amount:
                level = Levels.index(amount)

        return level

    def getTotalExp(self):
        total = 0
        for level in self.experience:
            total += level

        return total

    def getNextExpValue(self, track, curSkill=None):
        if not curSkill:
            curSkill = self.experience[track]
        retVal = Levels[len(Levels) - 1]
        for amount in Levels:
            if curSkill < amount:
                retVal = amount
                return retVal

        return retVal

    def getNewGagIndexList(self, track, extraSkill):
        retList = []
        curSkill = self.experience[track]
        nextExpValue = self.getNextExpValue(track, curSkill)
        finalGagFlag = 0
        while curSkill + extraSkill >= nextExpValue > curSkill and not finalGagFlag:
            retList.append(Levels.index(nextExpValue))
            newNextExpValue = self.getNextExpValue(track, nextExpValue)
            if newNextExpValue == nextExpValue:
                finalGagFlag = 1
            else:
                nextExpValue = newNextExpValue

        return retList
