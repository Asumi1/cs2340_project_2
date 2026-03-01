from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobboard', '0011_message_notification_savedsearch'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedsearch',
            name='last_match_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
