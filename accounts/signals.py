from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    UserProfile creation is handled explicitly in views.py
    so that the correct role and approval status can be assigned.
    """
    pass