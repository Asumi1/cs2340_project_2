from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_jobseekerprofile_latitude_jobseekerprofile_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobseekerprofile',
            name='preferred_commute_radius_miles',
            field=models.PositiveIntegerField(default=25, help_text='Preferred commute radius in miles for map filtering'),
        ),
    ]
