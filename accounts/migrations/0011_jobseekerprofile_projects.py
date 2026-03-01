from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_jobseekerprofile_preferred_commute_radius_miles'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobseekerprofile',
            name='projects',
            field=models.TextField(blank=True, help_text='Projects and portfolio highlights'),
        ),
    ]
