import re
from time import sleep
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from datetime import datetime

from django.conf import settings

from django.db import connection, transaction

from . rfid_sock import modify_user, remove_rfid_from_EEPROM

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

11/01/2025 Apple
Updating code to run with Django 5.2.6 python 3.13.5

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
        logger.info(f"An error occurred adding tag to delete queue: {e}")


# Important stuff **    

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Other fields here
    rfid_access = models.BooleanField(default=False)
    rfid_tag = models.CharField(max_length=20,blank=True,null=True,unique=True)
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
        #adding a try block around the save method just in case :)
        try:
            models.Model.save(self, *args, **kwargs)
        except IntegrityError as e:
            # Handle database integrity errors (e.g., unique constraint violation)
            logger.info(f"Database error: {e}")
        except ValidationError as e:
            # Handle validation errors (if raised within save or pre_save)
            logger.info(f"Validation error: {e.message_dict}")
        except Exception as e:
            # Catch any other unexpected exceptions
            logger.info(f"An unexpected error occurred: {e}")
            

    def __str__(self):
        return self.user.username + "'s profile"


# using python decoration to run this after User creation

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    logger.info(F" after User creation to create user_profile")
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except IntegrityError as e:
            # Handle specific integrity errors (e.g., user already has a profile)
            logger.info(f"Integrity error: {e}")
        except ValidationError as e:
            # Handle validation errors
            logger.info(f"Validation error: {e}")
        except Exception as e:
            # Handle other potential exceptions
            logger.info(f"An unexpected error occurred: {e}")




# tie to User deletion

# using python decoration to run this funtion befor deletion takes place

@receiver(pre_delete, sender=User)
def profile_in_delete_queue(sender, instance, **kwargs):
    logger.info("user about to be deleted, see if we need to put in queue")
    try:
        existing = UserProfile.objects.all().get(user=instance)
#        if existing.rfid_tag:
#            add_tag_to_delete_queue(existing.rfid_tag)
    

    except UserProfile.DoesNotExist:
        logger.info("fuck, couldn't find profile for %s" % instance)
    except Exception as e:
        logger.info(f"UserProfile not found with excp: {e}")

    if existing:
        rfid_tag = existing.rfid_tag
        try:
            existing.delete()

        except ProtectedError as e:
            # Handle the case where the object is protected
            logger.info(f"Deletion prevented due to protected related objects: {e.protected_objects}")
        except Exception as e:
            # Handle other potential exceptions
            logger.info(f"An error occurred:lr deleting UseProfile {e}")
            
        result = remove_rfid_from_EEPROM(settings.RFID_HOST, settings.RFID_PORT, rfid_tag,  settings.RFID_PASSWORD)
        logger.info(f"rfid_tag {rfid_tag} removed: {result}")   
        
#old way of adding signals
#post_save.connect(create_user_profile, sender=User)
#pre_delete.connect(profile_in_delete_queue, sender=User)

"""

for storing when we let ppl in

"""

class AccessEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_date = models.DateTimeField(auto_now = True)



