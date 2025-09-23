from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, pre_delete
from datetime import datetime

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

def add_tag_to_delete_queue(tag):
    from django.db import connection, transaction
    cursor = connection.cursor()
    # Data modifying operation - commit required
    cursor.execute("insert into rfid_user_delete_queue (rfid_tag, delete_date) values (%s,%s)", [tag, datetime.now()])
    transaction.commit_unless_managed()

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Other fields here
    rfid_access = models.BooleanField(default=False)
    rfid_tag = models.CharField(max_length=20,blank=True,null=True,unique=True)
    #rfid_in_eeprom = models.BooleanField(default=False) # changed from slot, which was unwieldy to manage.

    rfid_label = models.CharField(max_length = 50) # little label on the tag
    update_date = models.DateTimeField(null=True, blank = False, auto_now = True) # taking matters into my own hands...
    sync_date = models.DateTimeField(null=True, blank=True, auto_now = True, )
    #syncing = models.IntegerField(default = 0)

    def save(self, *args, **kwargs):
        print ("in da save, son")
        try:
            mask = 255 # actually this is the 'locked out' - 0 is the 'just log it'
            existing = UserProfile.objects.all().get(user=self.user)

            self.id = existing.id #force update instead of insert
            if (self.rfid_access):
                mask = 1
            print ("going for the EEPROM mod")
            if rfid_sock.modify_user(local_settings.RFID_HOST, local_settings.RFID_PORT, self.rfid_tag, mask, local_settings.RFID_PASSWORD):
                self.sync_date = datetime.now()
            # also set synch date, synching

        except UserProfile.DoesNotExist:
            pass
        models.Model.save(self, *args, **kwargs)

    def __str__(self):
        return self.user.username + "'s profile"

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# tie to User deletion
def profile_in_delete_queue(sender, instance, **kwargs):
    print ("user about to be deleted, see if we need to put in queue")
    try:
        existing = UserProfile.objects.all().get(user=instance)
        if existing.rfid_tag:
            add_tag_to_delete_queue(existing.rfid_tag)
    except UserProfile.DoesNotExist:
        print ("fuck, couldn't find profile for %s" % instance)

post_save.connect(create_user_profile, sender=User)
pre_delete.connect(profile_in_delete_queue, sender=User)

"""

for storing when we let ppl in

"""

class AccessEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_date = models.DateTimeField(auto_now = True)



