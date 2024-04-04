from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.

class UserAccountManager(BaseUserManager): # Overwrites the BaseUserManager class
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")
        
        user = self.model(
            email = self.normalize_email(email), #set to lowercase
            username = username,
        )

        # Hash the password
        user.set_password(password)
        # Save the user to database
        user.save()

        return user
    

class UserAccount(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def get_email(self):
        return self.email

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

