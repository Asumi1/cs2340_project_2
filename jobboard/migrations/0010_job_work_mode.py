from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobboard", "0009_alter_job_is_approved_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="work_mode",
            field=models.CharField(
                choices=[("ONSITE", "On-site"), ("REMOTE", "Remote")],
                default="ONSITE",
                max_length=20,
            ),
        ),
    ]
