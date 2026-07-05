from django.db import models


class Favorite(models.Model):
    """
    Persists a user-favorited NHANES variable.
    Keyed by column_name since variables live in the CSV artifact, not the DB.
    """
    column_name = models.CharField(max_length=64, unique=True)
    sas_label   = models.CharField(max_length=255, blank=True)
    component   = models.CharField(max_length=64,  blank=True)
    data_file   = models.CharField(max_length=64,  blank=True)
    added_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.column_name} — {self.sas_label}'
