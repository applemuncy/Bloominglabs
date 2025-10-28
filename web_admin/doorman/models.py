import re
from time import sleep
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from datetime import datetime

from django.conf import settings

from django.db import connection, transaction

from . rfid_sock import modify_user

import socket
from django_app.settings import setup_logging
import logging 
setup_logging()
logger = logging.getLogger(__name__)
logger.info("doorman/model.py")


"""

Some considerations:
Asynchronous connection to Arduino/Board Firmware.

8/21/2012
oh fuck, now date format via sqlite is fucked. B/c updated outside Django?

Try in this order
1) all date manipulation - use datetime (or SQL Standard for comparing)
2) Move to postgres

Point to ponder:
Ideally, very few ppl will be in eeprom at all times. So just add a sync function?
In the future if you have 'add user at the reader with the special 'add user' tag, ensure that gets fed back to the django db.
ensure simple func to id stuff to sync, do periodically in the daemon process (twisted)

1/1/2013
Add rfid sock func

"""

NOTIFICATION_TYPE_CHOICES = (
    ('Access', 'Door Unlocked'),
)

"""

catch deletes for sync purposes

"""


def add_tag_to_delete_queue(rfid_tag):
    try:
        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(F"insert into rfid_user_delete_queue (rfid_tag, delete_date) values ({rfid_tag}, {datetime.now()}")
    except Exception as e:
        print(f"An error occurred: {e}")


newpat =  re.compile(r"Tag: (\S+) successfully added with mask:(\S+)", re.M)


#move here from rfid_sock.py
"""
def modify_user(host, port, tag, mask, password):
    
    logger.info("modify_user ")
    logger.info(f"host: {host} port: {port}")
    client_rfid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_str = F"m {tag} {mask}${password}\r\n"
    logger.info(f"send data_str: {data_str}")

    try:
        client_rfid.connect((host, port))
        logger.info("client_rfid connected")
        client_rfid.sendall(data_str.encode('utf-8'))
        data_recv = client_rfid.recv(1024)
        returned_data_str = data_recv.decode("utf-8")
        logger.info(f"Receved from RFID {returned_data_str}")

    except ConnectionRefusedError:
        logger.info(f"Connection refused. Ensure the server is running on {SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        logger.info(f"An error occurred: {e}")
    finally:
        # Close the socket
        client_rfid.close()
        logger.info("Socket closed.")

    success = False
    match = newpat.search(returned_data_str)
    if match:
        logger.info("tag: %s mask %s\n" % (match.group(1), match.group(2)))
        success = True

    logger.info(F"returned_data_str: {returned_data_str}")
    logger.info(success)
    return success
"""
    

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Other fields here
    rfid_access = models.BooleanField(default=False)
    rfid_tag = models.CharField(max_length=20,blank=True,null=True,unique=True)
    #rfid_in_eeprom = models.BooleanField(default=False) # changed from slot, which was unwieldy to manage.

    rfid_label = models.CharField(max_length = 50) # little label on the tag
    update_date = models.DateTimeField(null=True, blank = False, auto_now = True) # taking matters into my own hands...

#sync_date hold the time the controller was last changed for this user.
    sync_date = models.DateTimeField(null=True, blank=True, auto_now = True, )
    #syncing = models.IntegerField(default = 0)

    def save(self, *args, **kwargs):
        logger.info("in da save, son")
        try:
            mask = 255 # actually this is the 'locked out' - 0 is the 'just log it'
            existing = UserProfile.objects.all().get(user=self.user)

            self.id = existing.id #force update instead of insert
            if (self.rfid_access):
                mask = 1
            logger.info("going for the EEPROM mod")
            logger.info(F"{settings.RFID_HOST},{ settings.RFID_PORT}, {self.rfid_tag},{ mask, settings.RFID_PASSWORD}")
            #modify_user() from "rfid_sock.py" handles writing new data to the RFID controller
            result = modify_user(settings.RFID_HOST, settings.RFID_PORT, self.rfid_tag, mask, settings.RFID_PASSWORD)
            if result:
                self.sync_date = datetime.now()
                logger.info("Success")
            else:
                logger.info("Something went wrong in modify_user")

        except UserProfile.DoesNotExist:
            pass
        models.Model.save(self, *args, **kwargs)

    def __str__(self):
        return self.user.username + "'s profile"

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# tie to User deletion
@receiver(pre_delete, sender=User)
def profile_in_delete_queue(sender, instance, **kwargs):
    logger.info("user about to be deleted, see if we need to put in queue")
    try:
        existing = UserProfile.objects.all().get(user=instance)
        if existing.rfid_tag:
            add_tag_to_delete_queue(existing.rfid_tag)
    except UserProfile.DoesNotExist:
        logger.info("fuck, couldn't find profile for %s" % instance)

post_save.connect(create_user_profile, sender=User)
#pre_delete.connect(profile_in_delete_queue, sender=User)

"""

for storing when we let ppl in

"""

class AccessEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_date = models.DateTimeField(auto_now = True)



