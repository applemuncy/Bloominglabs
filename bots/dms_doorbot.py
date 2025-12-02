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
sys.path.append('/home/pi/Bloominglabs/web_admin')
import logging
import subprocess, select
import irc.client
import irc.bot
import itertools
import random
import time, urllib
#, simplejson
import time
from time import sleep
import datetime
# for future investigation - weirdly from datetime import datetime didn't work!
# for network piece
import socket



upload_interval = 60 # seconds between uploading sensor/door reading
last_upload_time = datetime.datetime.now()
os.environ['DJANGO_SETTINGS_MODULE'] ="django_app.settings"
from django.conf import settings
import django
django.setup()

import threading
from queue import Queue
#global queues for irc bot and rfid reader
irc_q = Queue()
rfid_q = Queue()

# global flags for threads
rfid_stop_flag = False
irc_stop_flag = False


from  django_app.settings import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


logger.info("after django setup")

# port where the RFID server is running. put this in settings.py for the django
# server
RFID_PORT = settings.RFID_PORT
RFID_HOST = settings.RFID_HOST

IRC_PORT = settings.IRC_PORT
IRC_CHANNEL = settings.IRC_CHANNEL
IRC_NICKNAME = settings.IRC_NICKNAME    
IRC_SERVER = settings.IRC_SERVER

logger.info(f"port: {IRC_PORT}")
logger.info(f"IRC_CHANNEL: {IRC_CHANNEL}")
logger.info(f"nick: {IRC_NICKNAME}")
logger.info(f"server:: {IRC_SERVER}")
      
ircConn = None

guid = None
uid_denied = None
BotDied = False



from asgiref.sync import sync_to_async

os.environ['DJANGO_SETTINGS_MODULE'] ="settings"
from django.conf import settings

from django.db import models
from doorman.models import UserProfile, AccessEvent 
from django.contrib.auth.models import User
"""
logger = logging.getLogger('rfid_logger')
logging.basicConfig(filename='/home/pi/log/DMS.log', encoding='utf-8', level=logging.INFO)

logger.setLevel(logging.INFO)
fh = logging.FileHandler('rfid.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
fh.setFormatter(formatter)
ch.setFormatter(formatter)    


logger.addHandler(ch)

"""

logger.debug('This message should go to the log file')
logger.info('So should this')
logger.warning('And this, too')
logger.error('And non-ASCII stuff, too, like Øresund and Malmö')

#logging.addHandler(ch)

logger.info("RFID logger bot started.")

random.seed()
max_sleep = 1 # 'take a breath' after responding. prevent bots from making
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
authpat =  re.compile(r"User (\S+) granted access", re.M)

lockedoutpat = re.compile(r"User (\S+) locked out.", re.M)

deniedpat = re.compile(r"(\S+) denied access at reader", re.M)

# last command
last_command_pat = re.compile(r"\!last\s+(\d+|\s*)\s*(\S+)", re.M and re.IGNORECASE)

# just look for access message, if so gimme the user
def check_for_door(stuff):
    match = authpat.search(stuff)
    logger.info(f"stuff match: {match}")
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
    logger.info(f'match-last: {match}')
    if  match:
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
    if matches[1] == 'access':
        qs = AccessEvent.objects.order_by('-event_date')[:num]
        for q in qs:
            responses.append('%s at %s' % (q.user.username, q.event_date))
    else:
        responses = ('Command not understood. Types are  ''access'', you asked for %s' % matches[1],)

    logger.info(F'responces: {responses}')

    return responses

# like before but now both use these

def handle_msg(connection, event ):
    target = IRC_CHANNEL
    logger.info(f"connection: {connection}")

    logger.info("handle_msg")

    logger.info("event.type")
    logger.info(event.type)

    logger.info("event.source")
    logger.info(event.source)

    logger.info("event.target")
    logger.info(event.target)

    logger.info("event.arguments[0]")
    logger.info(event.arguments[0])

    IRC_message = event.arguments[0]

    stuff = ','.join(event.arguments)
    logger.info(f"stuff recieved: {stuff}")

    said = event.arguments[0]
    logger.info(f"said: {said}")
    (name,truename) = event.source.split('!')
    logger.info(f"name: {name} truename: {truename}")
    time.sleep(random.choice(range(max_sleep)))
    try:
        if stuff.upper().find(IRC_NICKNAME.upper()) >= 0:
        #if stuff.er().find('fantasticmagic') >= 0:
            if stuff.find('get lost')>=0: 
                connection.disconnect('AAGUUGGGHHHHHHuuaaaaa!')
                logger.info("Fuck it, I disconnected")
            else:
                connection.privmsg(target,u'%s, %s' % ('Type ''last n access''  to see recent accesses ',name))
                msg = random_greets[random.choice(range(len(random_greets)))] % name
                connection.privmsg(target,msg)
# handle last command (if anything came back)
        else:
            for r in last_command_responses(stuff):
                connection.privmsg(target,u'%s' % r)

    except Exception as val:
        logger.error("fail in pubmsg handle: (%s) (%s)" % (Exception, val))

def handle_privmsg(connection, event):
    logger.info("handle privmsg")
    handle_msg(connection, event)
#    handle_msg(connection, event, (event.source().split('!'))[0])


"""
kind of a big deal. handler of all msgs!
"""

def handle_pubmsg(connection, event  ):
    logger.info("handle pubmsg")
    handle_msg(connection, event )

def handle_join(client,event):
        (name,truename) = event.source().split('!')
        client.privmsg(IRC_CHANNEL,'%s!!!' % name.upper())

def log_door_event(connection, user_id):
    logger.info(f"log_door_event user_id: {user_id}")
    prof = None
    prof_QS = None
    try:

        prof = UserProfile.objects.get(rfid_tag__iexact = user_id)
        logger.info(f"prof type")
        logger.info(type(prof))
        logger.info(F"prof: {prof}")
        logger.info(F"prof obj: {prof.user.username}")

    except:
        logger.error(f"Strange: no username found in DB for user {user_id}." )
    username = 'UNKNOWN'
    if prof:
        # note can't log unknow this way, though
        logger.info(F"User name {prof.user.username}")
        event = AccessEvent(user = prof.user)
        event.save()
        username = prof.user.username
    logger.info("we see: %s aka %s" % (user_id, username))
    msg = "!s " + random_sez[random.choice(range(len(random_sez)))] %    username
    connection.privmsg(IRC_CHANNEL,msg)


#new IRC code

class MyBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, nickname, server, port=6667):
    # A SingleServerIRCBot simplifies connection and management.
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_welcome(self, connection, event):
        connection.join(self.channel)
        logger.info(F"Connected to {self.channel}")

        #the set_keepalive should handle reconnections after network troubles.
        connection.set_keepalive(600)

        global ircConn
        ircConn = connection
        return
# Called when a private message (privmsg) is received
    def on_privmsg(self, connection, event):
        self.do_command(connection, event)

    # Called when a channel message (pubmsg) is received
    def on_pubmsg(self, connection, event):
        self.do_command(connection, event)

    # The core logic for handling incoming messages
    def do_command(self, connection, event):
        source_nick = event.source.nick
        message_text = event.arguments[0]
        logger.info(f"[{self.channel}] <{source_nick}> {message_text}")
        
        # Echo the message back to the channel
        if event.target == self.channel:
            connection.privmsg(self.channel, f"Echo {self.channel}: {message_text}")
            handle_pubmsg(connection, event)

        else:
            # For private messages to the bot
            connection.privmsg(source_nick, f"Echo to  private by  bot: {message_text}")
    def on_die():
        global BotDied
        BotDied = True




def run_irc_bot():
    logger.info('run_bot started')
    bot = MyBot(IRC_CHANNEL, IRC_NICKNAME, IRC_SERVER, IRC_PORT)
    bot.start()

def read_rfid():
    run = True
    logger.info("read_rfid started")

    my_client =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    my_client.connect((
        RFID_HOST,
        RFID_PORT,
        ))
    logger.info(f'RFID_HOST:RFID_PORT {RFID_HOST}:{RFID_PORT}')
    
    logger.info("No loop anymore")
    
#    while run:   
    while (run):
        data =  my_client.recv(1024)
        data = data.decode()
        if data:

            data_s = data.split()
            if 'UNUSED' in data_s: 
                continue 
            else:
                rfid_q.put(data)
                logger.info(f"fresh data: {data}")

    


    logger.info("closing my_client")
    my_client.close()
         
def run_read_rfid():
    logger.info("inside run_read_rfid") 
    while True:
        read_rfid()

   

def on_connect(connection, event):
    connection.join(IRC_CHANNEL)
    logger.info("joined channel: {IRC_CHANNEL}")
    return

def handle_rfid_data_str(data):
    logger.info(f"stringy is: {data}")
#start by looking for door open event
    global uid

    uid = check_for_door(data)
    if uid:
        logger.info(F"open door evernt: {uid}")
        doorval = 1
        log_door_event(ircConn, uid)
        return



    uid = check_for_denied(data)
    global uid_denied
    if uid:
        logger.info(F"uid denied: {uid}")
        uid_denied = uid
        return               
        
    uid = check_for_lockedout(data)
    if uid:
        logger.info(F"lockedout uid: {uid}")

    time.sleep(1)
    

if __name__ == '__main__':
    logger.info("Started main:  logger.")
    



    irc_thread = threading.Thread(target = run_irc_bot)
    rfid_thread = threading.Thread(target = run_read_rfid)

    logger.info("Starting irc_thread")
    irc_thread.start()

    sleep(1)

    logger.info("Starting rfid .")
    rfid_thread.start();
#    run_read_rfid()
    
    


    logger.info("while forever")
    while True:
        if (not rfid_q.empty()):
            data = rfid_q.get()
            logger.info(f"data from rfid_q: {data}") 
            handle_rfid_data_str(data )


        if (guid != None):
            log_door_event(ircConn , guid)
            guid = None
        if(uid_denied != None):
            logger.info(F"Creating dummy: {uid_denied})")
            
            create_dummy(uid_denied)
            uid_denied = None

        time.sleep(1)

        if BotDied == True:
            logger.info("BotDied restarting")
            BotDied = False
            irc_stop_flag = True
            irc_thread.join()
            irc_stop_flag = False
            irc_thread = threading.Thread(target = run_irc_bot)
            irc_thread.start


    
       
