#! /usr/bin/env python3
"""
SDC 1/11/2012

Bot that says 'hi' on IRC channel when people are authenticated by the RFID

messages have the form:
18:50:21  1/11/12 WED 18:50:21  1/11/12 WED User 14 authenticated.
18:50:21  1/11/12 WED User  granted access at reader 1

1/12/2012

Note, this is fun, reads the msgs in a voice usin festival

http://brainwagon.org/2011/01/30/my-speech-bot-using-irclib-py/
he has some great Arduino/hacker stuff, too

irclib code is here:
http://forge.kasey.fr/projets/hashzor/irclib.py

1/14/2012 SDC
Using 'select' so pings are handled.
Note they say poll may be better here:
http://docs.python.org/library/select.html

for testing use 'UNREAL'
sudo ./unreal in the Unreal dir

3/1/2012 SDC
Database!

Note, depending where this 'lives', you will need to change DATABASE_NAME appropriately

3/12/2012

Auto-start on boot up.
remember the pogobox is now bloominglabs.no-ip.org

3/15/2012 SDC
PushingboxNotification up in here!

5/27/2012 SDC
RFID is now networked. Instead of reading a file, read a socket.

7/15/2012 SDC
Don't forget pachube yo

TODO - net (IRC) connectivity.
WTF w/ nohup?
general error handlin

7/15/2012 SDC
Don't forget pachube yo

9/30/2012 SDC
ever so minor logging conundrum.
When you get an event, it will set val = 1
but, only one will be set at a time.
so, when to set to zero? both may be triggered at more or less the same time. when to consider one (or both) 'off' when simultaneous activity.

How about (do this soon):
take office val/workshop val out.
when processing input, query the db. see if any events in last 10 sec. if so
send 1 else send 0. Duh.

11/9/2012 SDC
should really only log to pachube maybe once a minute for sensors anyway.

2/17/2013 SDC
add path for settings. moved to 'bots' dir. Where it belongs

3/22/2013 SDC
coding coders
some mods for RPi version + retry at startup.

7/16/2013 SDC
change logging level to warning

9/6/2016 SDC
Me again, dummy.
Need to create 'dummy user' when unknown tag presented.
I have a bad feeling about the tabbin'

Try dese

To look up the tag:

prfo = UserProfile.objects.get(rfid_tag__iexact = 'shit')


"""

import re, sys, os
sys.path.append('/home/apple/git/Bloominglabs/web_admin')
import logging
import subprocess, select
import irc.client
import random
import time, urllib, simplejson
import time
import datetime
# for future investigation - weirdly from datetime import datetime didn't work!
# for network piece
import socket
import sys


upload_interval = 60 # seconds between uploading sensor/door reading
last_upload_time = datetime.datetime.now()
os.environ['DJANGO_SETTINGS_MODULE'] ="settings"
from django.conf import settings


# port where the RFID server is running. put this in settings.py for the django
# server
RFID_PORT = settings.RFID_PORT
RFID_HOST = settings.RFID_HOST

from django.db import models
#from DoorMan.doorman.models import UserProfile, AccessEvent 
#from django.contrib.auth.models import User
"""
logger = logging.getLogger('rfid_logger')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('rfid.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
fh.setFormatter(formatter)
ch.setFormatter(formatter)    
"""

logging.basicConfig(filename='DMS.log', encoding='utf-8', level=logging.INFO)
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')
logging.error('And non-ASCII stuff, too, like Øresund and Malmö')

port = settings.IRC_PORT
channel = settings.IRC_CHANNEL
IRC_CHANNEL = settings.IRC_CHANNEL
nickname = settings.IRC_NICKNAME    
IRC_SERVER = settings.IRC_SERVER

#logger.addHandler(ch)

logging.info("RFID logger bot started.")

random.seed()
max_sleep = 3 # 'take a breath' after responding. prevent bots from making
# you make a damn fool of yourself

# %s - pass in name
random_sez = [
    'how about that local sports team, %s?',
    'hey there %s, let me get the door for you',
    'good day to you, %s',
    'great day for hacking there, %s',
    '%s in the hizous!',
    '%s has arrived',
    'Never fear, %s is here',
]

random_greets = [
    'Nice to see you, %s.',
    'Whatever %s.',
    'Well, %s, Lemonade was a popular drink in my time. And it still is!',
    'Tell it to the judge, %s.',
    'Thar\'s a snake in mah boot %s.',
    'You try doing this job %s.',
    'My cat\'s breath smells like catfood, %s.',
    'What you talking about, %s?',
    'YAWN! You woke me up, %s. Now what do ya want?',
]

# note. now have to do by tag. watch out for case sensitivity
authpat =  re.compile("User (\S+) granted access", re.M)

lockedoutpat = re.compile("User (\S+) locked out.", re.M)

deniedpat = re.compile("(\S+) denied access at reader", re.M)

# last command
last_command_pat = re.compile('\!last\s+(\d+|\s*)\s*(\S+)', re.M and re.IGNORECASE)

# just look for access message, if so gimme the user
def check_for_door(stuff):
    match = authpat.search(stuff)
    if match:
        return match.group(1)
    else:
        return None

def check_for_denied(stuff):
    match = deniedpat.search(stuff)
    if match:
        return match.group(1)
    else:
        return None

def check_for_lockedout(stuff):
    match = lockedoutpat.search(stuff)
    if match:
        return match.group(1)
    else:
        return None

"""

Thing for when you DON'T find the RFID that was entered.

TODO - what if it already exists???



"""
def create_dummy(rfid):
    # TODO: if user doesn't exist create dummy user - if it does, update the sync date(?)
    # first see if one there
    try:
        prfo = UserProfile.objects.get(rfid_tag__iexact = rfid)
        prfo.rfid_tag = prfo.rfid_tag + '-returned'
        prfo.save()
    except: # nothing found
        pass # yeah I know get off my back mom!
    n = datetime.datetime.now()
    username = "%s-dummy" % n.strftime('%Y-%m-%d-%H-%M-%S')
    # note gotta randomize password there
    user = User.objects.create_user(username, 'dummy@dummy.com',str(int(random.random() * 10000000)))
    user.save()
    up = UserProfile(user = user, rfid_access = False, rfid_tag = rfid)
    up.save()

def check_for_last_command(stuff):
    match = last_command_pat.search(stuff)
    if match:
        return match.groups()
    else:
        return None

def last_command_responses(stuff):
    matches = check_for_last_command(stuff)
    num = 1
    responses = []
    if not matches:
        return responses
    try:
        num = int(matches[0])
        if num > 10:
            num = 10 # don't flood the channel, son
    except:
        pass
    if matches[1] == 'sensor':
        qs = SensorEvent.objects.order_by('-event_date')[:num]
        for q in qs:
            responses.append('%s with value %s from sensor %s at %s' % (q.event_type, q.event_value, q.event_source, q.event_date))
    elif matches[1] == 'access':
        qs = AccessEvent.objects.order_by('-event_date')[:num]
        for q in qs:
            responses.append('%s at %s' % (q.user.username, q.event_date))
    else:
        responses = ('Command not understood. Types are ''sensor'' or ''access'', you asked for %s' % matches[1],)
    print(responses)
    return responses

# like before but now both use these

def handle_msg(connection, event ):
    logging.info("handle_msg\r")
    
    logging.info("channel")

    logging.info("event.type")
    logging.info(event.type)

    logging.info("event.source")
    logging.info(event.source)

    logging.info("event.target")
    logging.info(event.target)


    logging.info("event.arguments[0]")
    logging.info(event.arguments[0])

    print(event.arguments[0])

"""    
    stuff = ','.join(event.arguments())
    said = event.arguments()[0]

    (name,truename) = event.source().split('!')

    time.sleep(random.choice(range(max_sleep)))
    try:
        if stuff.upper().find(IRC_NICK.upper()) >= 0:
        #if stuff.er().find('fantasticmagic') >= 0:
            if stuff.find('get lost')>=0:
                 :w
                 client.disconnect('AAGUUGGGHHHHHHuuaaaaa!')
                logger.info("Fuck it, I disconnected")
            else:
#                client.privmsg(target,u'%s, %s' % ('Type ''last n access'' or ''last n sensor'' to see recent accesses or sensors',name))
                msg = random_greets[random.choice(range(len(random_greets)))] % name
                client.privmsg(target,msg)
# handle last command (if anything came back)
        else:
            for r in last_command_responses(stuff):
                client.privmsg(target,u'%s' % r)

    except Exception as val:
        logger.error("fail in pubmsg handle: (%s) (%s)" % (Exception, val))
"""
def handle_privmsg(connection, event):
    handle_msg(connection ,event, (event.source().split('!'))[0])


"""
kind of a big deal. handler of all msgs!
"""

def handle_pubmsg(connection, event  ):
    handle_msg(connection, event )

def handle_join(client,event):
        (name,truename) = event.source().split('!')
        client.privmsg(IRC_CHANNEL,'%s!!!' % name.upper())

def log_door_event(connection, user_id):
    prof = None
    try:
        prof = UserProfile.objects.get(rfid_tag__iexact = user_id)
    except:
        logger.error("Strange: no username found in DB for user %s." % user_id)
    username = 'UNKNOWN'
    if prof:
        # note can't log unknow this way, though
        event = AccessEvent(user = prof.user)
        event.save()
        username = prof.user.username
    logger.info("we see: %s aka %s" % (user_id, username))
    msg = "!s " + random_sez[random.choice(range(len(random_sez)))] % username
    connection.privmsg(IRC_CHANNEL,msg)




if __name__ == '__main__':
    logging.info("Started main:  logger.")
    logging.info("Started IRC .")

#    MDSbot = IrcBot(channel, nickname, server, port)
#    MDSbot.start()
    client = irc.client.IRC()
    server = client.server()
    server.connect(IRC_SERVER, port, nickname)
    server.join( channel, key="")

    server.privmsg(channel, "Hello")
    #client.add_global_handler("pubmsg" , handle_pubmsg(client , "pubmsg")) 
    client.add_global_handler("pubmsg" , handle_pubmsg)

        # connect up in this piece
    weConnected = False
    logging.info("Started RFID client.")

    rfid_client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    while not weConnected:
        try:
            rfid_client.connect((RFID_HOST,RFID_PORT))
            weConnected = True
            logging.info("Connected RFID socket.")

        except:
            logger.info("retrying connect to rfid in 10....")
            time.sleep(10)
            logging.info("Not Connected")
    stringy = ''
    doorval = 0
    officeval = 0
    workshopval = 0
    while True:
        doorval = 0
        officeval = 0
# Wait for input from stdin & socket 1 is timeout
        input_ready, output_ready,except_ready = select.select([rfid_client], [],[],1)
        while input_ready:
        # you could have multiple
            for i in input_ready:
                if i == rfid_client:
                    charry = rfid_client.recv(1).decode("utf-8")
                    stringy = stringy + charry

                    uid = check_for_denied(stringy)
                    if uid:
                        create_dummy(uid)
                    uid = check_for_lockedout(stringy)
                    if uid:
                        create_dummy(uid)
                    uid = check_for_door(stringy)
                    if uid:
                        doorval = 1
                        log_door_event(ircConn, uid)
                        time.sleep(3)
                        stringy = ''
            input_ready, output_ready,except_ready = select.select([rfid_client], [],[],1)
        try:
            if (datetime.datetime.now() - last_upload_time).total_seconds() > upload_interval:
                last_upload_time = datetime.datetime.now()
                logging.info("let's do some pachube shit")
                doorval = 0
                officeval = 0
                workshopval = 0

        except Exception as val:
            print("cosm probs: %s, %s" % (Exception, val))
            logging.error("IRC/pachube update problems: %s:%s" % (Exception, val))
            
        client.process_once(2)
        time.sleep(5)

