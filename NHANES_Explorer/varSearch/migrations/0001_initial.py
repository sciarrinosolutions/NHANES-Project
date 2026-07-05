from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('column_name', models.CharField(max_length=64, unique=True)),
                ('sas_label',   models.CharField(blank=True, max_length=255)),
                ('component',   models.CharField(blank=True, max_length=64)),
                ('data_file',   models.CharField(blank=True, max_length=64)),
                ('added_at',    models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-added_at']},
        ),
    ]
