from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_jobseekerprofile_bio_jobseekerprofile_linkedin_url_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='jobseekerprofile',
            name='profile_photo',
            field=models.ImageField(blank=True, null=True, upload_to='profile_photos/'),
        ),
        migrations.AddField(
            model_name='recruiterprofile',
            name='profile_photo',
            field=models.ImageField(blank=True, null=True, upload_to='profile_photos/'),
        ),
    ]