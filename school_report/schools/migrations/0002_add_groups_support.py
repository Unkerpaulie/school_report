# Generated manually for groups support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0001_initial'),
    ]

    operations = [
        # Add groups_per_standard field to School model
        migrations.AddField(
            model_name='school',
            name='groups_per_standard',
            field=models.PositiveIntegerField(default=1, help_text='Number of groups/classes per standard level (applies to all standards)'),
        ),
        
        # Add group_number field to Standard model
        migrations.AddField(
            model_name='standard',
            name='group_number',
            field=models.PositiveIntegerField(default=1, help_text='Group number within this standard level'),
        ),
        
        # Remove old unique constraint
        migrations.AlterUniqueTogether(
            name='standard',
            unique_together=set(),
        ),
        
        # Add new unique constraint including group_number
        migrations.AlterUniqueTogether(
            name='standard',
            unique_together={('school', 'name', 'group_number')},
        ),
        
        # Update ordering
        migrations.AlterModelOptions(
            name='standard',
            options={'ordering': ['name', 'group_number']},
        ),
    ]
