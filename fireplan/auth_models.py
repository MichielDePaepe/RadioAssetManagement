# fireplan/auth_models.py
from django.conf import settings
from django.db import models


class FireplanLanguage(models.Model):
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.code or self.label


class FireplanGrade(models.Model):
    # Fireplan levert hier de FR-tekst → die stoppen we in 'name'
    name = models.CharField(max_length=150, unique=True)
    # Afkorting, ook meertalig via modeltranslation
    abbrev = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name or self.abbrev or "Grade"


class FireplanGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class FireplanSubGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class FireplanFiliere(models.Model):
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.code


class FireplanProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fireplan_profile",
    )

    fireplan_username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Username used to log in to Fireplan",
    )

    language = models.ForeignKey(
        FireplanLanguage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    grade = models.ForeignKey(
        FireplanGrade,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    groups = models.ForeignKey(
        FireplanGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    subgroups = models.ForeignKey(
        FireplanSubGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )
    filiere = models.ForeignKey(
        FireplanFiliere,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profiles",
    )

    def __str__(self):
        name = f"{self.user.first_name} {self.user.last_name}"
        if self.grade:
            return f"{self.grade.abbrev} {name}"
        return name
