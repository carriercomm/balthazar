#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright 2007-2014 Sean Bruen. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY SEAN BRUEN ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL SEAN BRUEN OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied.


import ConfigParser
import MySQLdb
import os
import re
import signal
import telnetlib
import threading
from string import join, strip
from sys import exit
from time import localtime, sleep, strftime

__version__ = '$Id$'
sql = None
db = None
balthazar = telnetlib.Telnet()
ANSICOLOR_RE = re.compile(chr(27) + '\[[0-9;]*[m]')
ANSI_RE = re.compile('( |[A-Z])\x08')
STATLINE_RE = re.compile('(\\[HP=(\\d+)\\]:)')
bbs = {}
menu = {}
mysql = {}
report = {}
sw = {'who': 0, 'top': 0, 'topg': 0}
www = {}
debug = {}
_debug = 1


def main():
    """ initialize variables and config """
    global ANSI_RE, ANSICOLOR_RE, STATLINE_RE
    global bbs, balthazar, menu, start, sw, www
    global db, debug, sql, _debug
    config()
    if _debug: plog('intializing...')
    signal.signal(signal.SIGINT, quit)

    """ start telnet/threaded timer """
    thread1 = threading.Timer(30.0, threaded_timer)
    thread1.start()
    report[0] = 1
    report[1] = 1
    db = _db(mysql['host'], mysql['port'], mysql['user'], mysql['passwd'], \
             mysql['db'])
    sql = db.cursor()
    _telnet()
    balthazar.write('\r\n')
    while 1:
        try:
            line = balthazar.read_until('\r\n')
        except EOFError:
            if (_debug): plog('character %s lost connection!' % bbs['user'])
            quit()
        line = line.strip('\r\n')
        line = ANSICOLOR_RE.sub('', line)
        line = ANSI_RE.sub('', line)
        line = STATLINE_RE.sub('', line)
        if sw['who']: who_online(line)
        elif sw['top']: top_users(line)
        elif sw['topg']: top_gangs(line)
        """ uncomment for line by line output """
#        if _debug: mlog('%s' % line)
        gossip_log(line)
    return 0

def config():
    """ populate lists with configuration information """
    global bbs, debug, menu, www, _debug
    cfg = ConfigParser.ConfigParser()
    directory = os.path.dirname(os.path.realpath(__file__))
    cfg.read(directory+'/bbs.cfg')
    bbs['host'] = cfg.get('BBS', 'host', 1)
    bbs['port'] = int(cfg.get('BBS', 'port', 1))
    bbs['user'] = cfg.get('BBS','user', 1)
    bbs['muduser'] = cfg.get('BBS','muduser', 1)
    bbs['passwd'] = cfg.get('BBS','passwd', 1)
    bbs['admin'] = cfg.get('BBS', 'admin', 1)
    menu['main'] = cfg.get('MENU', 'main', 1)
    menu['pause'] = cfg.get('MENU', 'pause', 1)
    menu['mud'] = cfg.get('MENU', 'mud', 1)
    menu['go'] = cfg.get('MENU', 'go', 1)
    mysql['host'] = cfg.get('MYSQL', 'host', 1)
    mysql['port'] = int(cfg.get('MYSQL', 'port', 1))
    mysql['user'] = cfg.get('MYSQL', 'user', 1)
    mysql['passwd'] = cfg.get('MYSQL', 'passwd', 1)
    mysql['db'] = cfg.get('MYSQL', 'db', 1)
    debug['log'] = int(cfg.get('DEBUG', 'log', 1))
    debug['logfile'] = cfg.get('DEBUG', 'logfile', 1)
    if not _debug:
        _debug = int(cfg.get('DEBUG', 'verbose', 1))
    return 0

def plog(text):
    """ debug log """
    global debug
    if debug['log']:
        log = open(debug['logfile'], 'a')
        time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
        log.write('%s balthazar: %s\n' % (time, text))
    time = strftime('%H:%M:%S', localtime())
    #print '%s balthazar: %s' % (time, text)
    if (debug['log']): log.close()
    return 0

def mlog(text):
    """ debug mud log """
    global debug
    if debug['log']:
        log = open(debug['logfile'], 'a')
        time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
        log.write('%s: %s\n' % (time, text))
    time = strftime('%H:%M:%S', localtime())
    #print '%s: %s' % (time, text)
    if debug['log']: log.close()
    return 0

def quit(*args):
    """ stop telnet/threaded timer and exit """
    global balthazar, sql, _debug
    if _debug: plog('%d terminating...\n' % threading.active_count())
    balthazar.close()
    sql.close()
    exit(0)

def _telnet():
    """ telnet connectivity """
    global bbs, balthazar, menu, _debug
    try:
        balthazar.open(bbs['host'], bbs['port'])
        data = balthazar.read_until('login:')
        balthazar.write('%s\r\n' % bbs['user'])
        data = balthazar.read_until('password:')
        balthazar.write('%s\r\n' % bbs['passwd'])
    except:
        plog('telnet connection refused.\n - check config: bbs.cfg\n')
        exit(1)
    """ enter majormud """
    while 1:
        data = balthazar.read_very_eager()
        if menu['pause'] in data:
            balthazar.write('\r\n')
        elif menu['main'] in data:
            balthazar.write('%s\r\n' % menu['go'])
        elif menu['mud'] in data:
            balthazar.write('E\r\n')
        elif '[HP=' in data:
            bbs['conn'] = 1
            if _debug: plog('character %s on %s connected.' % (bbs['user'], bbs['host']))
            break
    return 0

def _db(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWD, DATABASE_NAME):
    """ mysql database connectivity """
    try:
        db = MySQLdb.connect(host=DATABASE_HOST,user=DATABASE_USER,passwd=DATABASE_PASSWD, port=int(DATABASE_PORT), db=DATABASE_NAME)
    except MySQLdb.OperationalError:
        plog('error connecting to mysql database.\n - check config: bbs.cfg\n')
        exit(1)

    plog('database %s on %s connected.' % (DATABASE_NAME, DATABASE_HOST))
    return db

def _sql(SQL_STRING, RET = 0):
    global _debug, db, sql
    data = None
    count = None
    try:
        count = sql.execute(SQL_STRING)
        if RET == 1: data=sql.fetchone()
        elif RET == 2: data=sql.fetchall()
        else: db.commit()
    except:
        db.rollback()
        if _debug: plog('db rollback')
    if RET > 0: return data
    else: return count

def threaded_timer():
    """ thread #1 - timer control """
    global bbs, balthazar, report, sw, _debug
    if not bbs['conn']: exit(0)
    """ debug: announce report loop number """
    if _debug and report[0] >= 1: plog('thread #1 - report #%d' % report[0])

    """ pull up who's online (30s) """
    sw['who'] = 1
    cmd = '/' + bbs['muduser'] + ' #who'
    try:
        _sql('TRUNCATE TABLE online')
        balthazar.write('who\r\n')
        sleep(0.5)
        balthazar.write(cmd+'\r\n')
        sleep(2)
    except:
        if _debug: plog('character %s lost connection!' % bbs['user'])
        quit()

    if report[1] == 10:
        """ pull up top 100 users (300s) """
        sw['top']=1
        cmd = '/'+bbs['muduser']+' #top'
        try:
            balthazar.write('top 100\r\n')
            sleep(2.5)
            balthazar.write(cmd+'\r\n')
            sleep(2)
        except:
            if _debug: plog('character %s lost connection!' % bbs['user'])
            quit()

        """ pull up top 100 gangs (300s) """
        sw['topg']=1
        cmd = '/' + bbs['muduser'] + ' #topgangs'
        try:
            balthazar.write('top 100 gangs\r\n')
            sleep(2.5)
            balthazar.write(cmd+'\r\n')
        except:
            if _debug: plog('character %s lost connection!' % bbs['user'])
            quit()
        report[1] = 0

    """ restart timer """
    report[0] = report[0] + 1
    report[1] = report[1] + 1
    thread1 = threading.Timer(30.0, threaded_timer)
    thread1.start()
    return 0

def gossip_log(text):
    """ gossip chat logger """
    global db, sql, _debug
    line = text.split(' ')
    try:
        if not line[1] == 'gossips:': return 0
    except IndexError:
        return 0
    name = line[0]
    gossip = join(line[2:], ' ')
    if (_debug): mlog('gossip: ('+name+') "'+gossip+'"')
    sqlstr = 'INSERT INTO gossip (name, text) VALUES (\'%s\',\'%s\')' % (name, gossip)
    _sql(sqlstr)
    return 0

def who_online(text):
    """ whos online """
    global bbs, sw
    if 'telepathing to yourself' in text: sw['who'] = 0
    if filtr(text):
        """ optional debug output """
        if (_debug): mlog('who: "'+text+'"')
        alignment = strip(text[0:8])
        gang = None
        if ' -  ' in text[9:]:
            tmp = text[9:].split(' -  ')
            schar = '-'
        else:
            tmp = text[9:].split(' x  ')
            schar = 'x'
        if len(tmp) > 1:
            name = strip(tmp[0])
            other = tmp[1]
            other = other.split('  of ')
        if len(other) > 1:
            title = strip(other[0])
            gang = strip(other[1])
            """ print statement for website formatting """
#            print '%8s %-20s %s  %s  of %s' % (alignment, name, schar, title, gang)
        else:
            title = strip(other[0])
            gang = ''
            """ print statement for website formatting """
#            print '%8s %-20s %s  %s' % (alignment, name, schar, title)
        sqlstr = 'INSERT INTO online (user, busy) VALUES (\'%s\', \'%s\')' % (name, schar)
        tmp = _sql(sqlstr)
        sqlstr = 'SELECT id FROM users WHERE user LIKE \'%s%%\'' % name
        tmp = _sql(sqlstr, 1)
        if not tmp == None:
            sqlstr = 'UPDATE users SET alignment = \'%s\', title = \'%s\', gang = \'%s\' WHERE id = \'%d\'' % (alignment, title, gang, tmp[0])
            tmp = _sql(sqlstr)
        else:
            sqlstr = 'INSERT INTO users (user, alignment, title, gang) VALUES (\'%s\', \'%s\', \'%s\', \'%s\')' % (name, alignment, title, gang)
            tmp = _sql(sqlstr)
    return 0

def top_users(text):
    """ top 100 users """
    global bbs, sw
    if 'telepathing to yourself' in text: sw['top'] = 0
    if filtr(text):
        """ optional debug output """
        if _debug: mlog('top: "'+text+'"')
        rank = strip(text[0:3])
        name = strip(text[5:26])
        cls = strip(text[27:37])
        gang = strip(text[38:57])
        if gang == 'None': gang=''
        exp = strip(text[58:])
        """ add/update user in database """
        sqlstr = 'SELECT exp FROM users WHERE user LIKE \'%s%%\'' % name
        tmp = _sql(sqlstr, 1)
        if tmp == None:
            sqlstr = 'INSERT INTO users (user, class, exp, expold, gang) VALUES (\'%s\', \'%s\', %s, %s, \'%s\')' % (name, cls, exp, exp, gang)
        else:
            expold = tmp[0]
            if tmp[0] > 0:
                sqlstr = 'UPDATE users SET class = \'%s\', exp = %s, expold = %d, gang = \'%s\' WHERE user LIKE \'%s%%\'' % (cls, exp, expold, gang, name)
            else:
                sqlstr = 'UPDATE users SET class = \'%s\', exp = %s, expold = %s, gang = \'%s\' WHERE user LIKE \'%s%%\'' % (cls, exp, exp, gang, name)
        tmp = _sql(sqlstr)
        """ add/update gang in database """
        sqlstr = 'SELECT exp FROM gangs WHERE gang LIKE \'%s%%\'' % gang
        tmp = _sql(sqlstr, 1)
        if tmp == None:
            sqlstr = 'INSERT INTO gangs (gang) VALUES (\'%s\')' % gang
            tmp=_sql(sqlstr)
        """ print statement for website formatting """
#        print '%3s. %-21s %-10s %-19s %-s' % (rank, name, cls, gang, exp)
    return 0

def top_gangs(text):
    """ top 100 users """
    global bbs, sw
    if 'telepathing to yourself' in text: sw['topg'] = 0
    if filtr(text):
        """ optional debug output """
        if _debug: mlog('topg: "'+text+'"')
        rank = strip(text[0:3])
        name = strip(text[5:24])
        leader = strip(text[25:36])
        members = strip(text[37:44])
        creation = strip(text[45:57])
        exp = strip(text[58:])
        sqlstr = 'SELECT exp FROM gangs WHERE gang LIKE \''+name+'%\''
        tmp = _sql(sqlstr, 1)
        if tmp == None:
            sqlstr = 'SELECT user FROM users WHERE user LIKE \''+leader+'%\''
            tmp = _sql(sqlstr, 1)
            if not tmp == None: leader = tmp[0]
            sqlstr = 'INSERT INTO gangs (gang, leader, members, exp, expold, creation) VALUES (\''+name+'\', \''+leader+'\', \''+members+'\', \''+exp+'\', \''+exp+'\', \''+creation+'\')'
            tmp = _sql(sqlstr)
        else:
            expold = tmp[0]
            if expold > 0:
                sqlstr = 'UPDATE gangs SET leader = \'%s\', members = \'%s\', exp = %s, expold = %d, creation = \'%s\' WHERE gang LIKE \'%s%%\'' % (leader, members, exp, expold, creation, name)
            else:
                sqlstr = 'UPDATE gangs SET leader = \'%s\', members = \'%s\', exp = %s, expold = %s, creation = \'%s\' WHERE gang LIKE \'%s%%\'' % (leader, members, exp, exp, creation, name)
            tmp = _sql(sqlstr)
        """ print statement for website formatting """
#        print '%3s. %-19s %-11s %-7s %-12s %s' % (rank, name, leader, members, creation, exp)
    return 0

def filtr(text):
    global bbs
    cmd = '/' + bbs['muduser'] + ' #who'
    if text == cmd: return 0
    cmd = '/' + bbs['muduser'] + ' #top'
    if text == cmd: return 0
    cmd = '/' + bbs['muduser'] + ' #topgangs'
    if text == cmd: return 0
    if 'Current Adventurers' in text: return 0
    elif '===================' in text: return 0
    elif 'Top Heroes of the Realm' in text: return 0
    elif 'Top Gangs of the Realm' in text: return 0
    elif '=-=-=-=-=-=-=-=-=-' in text: return 0
    elif 'Rank Name                  Class' in text: return 0
    elif 'Rank Gangname            Leader' in text: return 0
    elif text == 'top 100 gangs': return 0
    elif text == 'top 100': return 0
    elif text == 'who': return 0
    elif text == '': return 0
    elif ' gossips: ' in text: return 0
    elif ' says "' in text: return 0
    elif ' just disconnected!!!' in text: return 0
    elif ' just entered the Realm.' in text: return 0
    elif ' telepaths: ' in text: return 0
    elif 'Why are you telepathing to yourself?' in text: return 0
    else: return 1


if __name__ == '__main__':
    main()
