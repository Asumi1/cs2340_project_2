from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobboard', '0012_savedsearch_last_match_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedsearch',
            name='project',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
