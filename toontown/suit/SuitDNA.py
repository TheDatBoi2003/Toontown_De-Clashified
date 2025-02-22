import random
from panda3d.core import *
from direct.directnotify.DirectNotifyGlobal import *
from toontown.battle.SuitBattleGlobals import *
from toontown.toonbase import TTLocalizer
import random
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from otp.avatar import AvatarDNA

notify = directNotify.newCategory('SuitDNA')
suitHeadTypes = ['f',
                 'p',
                 'ym',
                 'mm',
                 'ds',
                 'hh',
                 'cr',
                 'tbc',
                 'bf',
                 'b',
                 'dt',
                 'ac',
                 'bs',
                 'sd',
                 'le',
                 'bw',
                 'sc',
                 'pp',
                 'tw',
                 'bc',
                 'nc',
                 'mb',
                 'ls',
                 'rb',
                 'cc',
                 'tm',
                 'nd',
                 'gh',
                 'ms',
                 'tf',
                 'm',
                 'mh',
                 'fc',
                 'af',
                 'ps',
                 'tr',
                 'gk',
                 'fm']
suitATypes = ['ym',
              'hh',
              'tbc',
              'dt',
              'bs',
              'le',
              'bw',
              'pp',
              'nc',
              'rb',
              'nd',
              'tf',
              'm',
              'mh',
              'af',
              'tr',
              'foreman']
suitBTypes = ['p',
              'ds',
              'b',
              'ac',
              'sd',
              'bc',
              'ls',
              'tm',
              'ms',
              'fm']
suitCTypes = ['f',
              'mm',
              'cr',
              'bf',
              'sc',
              'tw',
              'mb',
              'cc',
              'gh',
              'fc',
              'ps',
              'gk']
suitNamesByDept = {'c': ['f', 'p', 'ym', 'mm', 'ds', 'hh', 'cr', 'tbc'],
                    'l': ['bf', 'b', 'dt', 'ac', 'bs', 'sd', 'le', 'bw'],
                    'm': ['sc', 'pp', 'tw', 'bc', 'nc', 'mb', 'ls', 'rb'],
                    's': ['cc', 'tm', 'nd', 'gh', 'ms', 'tf', 'm', 'mh', 'fc', 'ps', 'af', 'tr', 'gk', 'fm']}
specialNamesByDept = {'s': ['foreman']}
suitDepts = ['c',
             'l',
             'm',
             's']
suitDeptFullnames = {'c': TTLocalizer.Bossbot,
                     'l': TTLocalizer.Lawbot,
                     'm': TTLocalizer.Cashbot,
                     's': TTLocalizer.Sellbot}
suitDeptFullnamesP = {'c': TTLocalizer.BossbotP,
                      'l': TTLocalizer.LawbotP,
                      'm': TTLocalizer.CashbotP,
                      's': TTLocalizer.SellbotP}
corpPolyColor = VBase4(0.95, 0.75, 0.75, 1.0)
legalPolyColor = VBase4(0.75, 0.75, 0.95, 1.0)
moneyPolyColor = VBase4(0.65, 0.95, 0.85, 1.0)
salesPolyColor = VBase4(0.95, 0.75, 0.95, 1.0)
suitsPerLevel = [1,
                 1,
                 1,
                 1,
                 1,
                 1,
                 1,
                 1]
suitsPerDept = 8
goonTypes = ['pg', 'sg']


def getSuitBodyType(name):
    if name in suitATypes:
        return 'a'
    elif name in suitBTypes:
        return 'b'
    elif name in suitCTypes:
        return 'c'
    else:
        print 'Unknown body type for suit name: ', name


def getSuitDept(name):
    for i in suitDepts:
        if name in suitNamesByDept[i]:
            return i
    print 'Unknown dept for suit name: ', name
    return None


def getSpecialDept(name):
    for i in suitDepts:
        if name in specialNamesByDept[i]:
            return i
    print 'Unknown dept for suit name: ', name
    return None


def getSuitDataOfDept(dept):
    suitDict = {}
    for name in suitNamesByDept[dept]:
        suitDict[name] = SuitAttributes[name]
    return suitDict


def getSuitDataOfDeptAndLvl(dept, lvl, maxTier=7):
    suitDict = getSuitDataOfDept(dept)
    levelDict = {}
    for name in suitNamesByDept[dept]:
        for i in xrange(0, len(suitDict[name]['hp'])):
            if suitDict[name]['level'] + i == lvl - 1 and suitDict[name]['level'] <= maxTier:
                levelDict[name] = suitDict[name]
                break
    return levelDict


def getDeptFullname(dept):
    return suitDeptFullnames[dept]


def getDeptFullnameP(dept):
    return suitDeptFullnamesP[dept]


def getSuitDeptFullname(name):
    return suitDeptFullnames[getSuitDept(name)]


def getSuitType(name):
    index = suitHeadTypes.index(name)
    return index % suitsPerDept + 1


def getRandomSuitType(level):
    return random.randint(max(level - 4, 1), min(level, 8))


def getRandomSuitByDept(dept):
    deptNumber = suitDepts.index(dept)
    return suitHeadTypes[suitsPerDept * deptNumber + random.randint(0, 7)]


class SuitDNA(AvatarDNA.AvatarDNA):

    def __init__(self, str=None, type=None, dna=None, r=None, b=None, g=None):
        if str:
            self.makeFromNetString(str)
        elif type:
            if type == 's':
                self.newSuit()
        else:
            self.type = 'u'
        return

    def __str__(self):
        if self.type == 's':
            return 'type = %s\nbody = %s, dept = %s, name = %s' % ('suit',
                                                                   self.body,
                                                                   self.dept,
                                                                   self.name)
        elif self.type == 'b':
            return 'type = boss cog\ndept = %s' % self.dept
        else:
            return 'type undefined'

    def makeNetString(self):
        dg = PyDatagram()
        dg.addFixedString(self.type, 1)
        if self.type == 's':
            dg.addFixedString(self.name, 3)
            dg.addFixedString(self.dept, 1)
        elif self.type == 'b':
            dg.addFixedString(self.dept, 1)
        elif self.type == 'u':
            notify.error('undefined avatar')
        else:
            notify.error('unknown avatar type: ', self.type)
        return dg.getMessage()

    def makeFromNetString(self, string):
        dg = PyDatagram(string)
        dgi = PyDatagramIterator(dg)
        self.type = dgi.getFixedString(1)
        if self.type == 's':
            self.name = dgi.getFixedString(3)
            self.dept = dgi.getFixedString(1)
            self.body = getSuitBodyType(self.name)
        elif self.type == 'b':
            self.dept = dgi.getFixedString(1)
        else:
            notify.error('unknown avatar type: ', self.type)
        return None

    def __defaultGoon(self):
        self.type = 'g'
        self.name = goonTypes[0]

    def __defaultSuit(self):
        self.type = 's'
        self.name = 'ds'
        self.dept = getSuitDept(self.name)
        self.body = getSuitBodyType(self.name)

    def newSuit(self, name=None, special=0):
        if not name:
            self.__defaultSuit()
        elif special:
            self.type = 'm'
            self.name = name
            self.dept = getSpecialDept(self.name)
            self.body = getSuitBodyType(self.name)
        else:
            self.type = 's'
            self.name = name
            self.dept = getSuitDept(self.name)
            self.body = getSuitBodyType(self.name)
        return

    def newBossCog(self, dept):
        self.type = 'b'
        self.dept = dept

    def newSuitRandom(self, level=0, dept=None, maxTier=7):
        self.type = 's'
        if level < 0 or level > HIGHEST_SUIT_LVL:
            notify.error('Invalid suit level: %d' % level)
        if dept is None:
            dept = random.choice(suitDepts)
        self.dept = dept
        possibleSuits = list(getSuitDataOfDeptAndLvl(dept, level, maxTier).keys())
        notify.debug("For level %s %s: %s..." % (level, dept, possibleSuits))
        self.name = random.choice(possibleSuits)
        notify.debug("Let's pick %s" % self.name)
        self.body = getSuitBodyType(self.name)
        return

    def newGoon(self, name=None):
        if type is None:
            self.__defaultGoon()
        else:
            self.type = 'g'
            if name in goonTypes:
                self.name = name
            else:
                notify.error('unknown goon type: ', name)
        return

    def getType(self):
        if self.type == 's':
            type = 'suit'
        elif self.type == 'b':
            type = 'boss'
        else:
            notify.error('Invalid DNA type: ', self.type)
        return type
