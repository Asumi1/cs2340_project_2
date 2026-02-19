from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_remove_recruiterprofile_profile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="recruiterprofile",
            name="profile_photo",
            field=models.ImageField(blank=True, null=True, upload_to="profile_photos/"),
        ),
    ]
