# Generated by Django 5.2.1 on 2025-06-07 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0001_initial'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='schoolstaff',
            options={'ordering': ['-year__start_year', 'staff__user__last_name', 'staff__user__first_name'], 'verbose_name': 'School Staff', 'verbose_name_plural': 'School Staff'},
        ),
        migrations.AlterField(
            model_name='schoolyear',
            name='start_year',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterUniqueTogether(
            name='schoolyear',
            unique_together={('school', 'start_year')},
        ),
    ]
