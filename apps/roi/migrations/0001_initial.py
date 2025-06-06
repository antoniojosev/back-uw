# Generated by Django 5.2 on 2025-04-19 21:04

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ROI',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('deposit_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('level', models.IntegerField(choices=[(1, 'Level 1: $100 - 30% ROI'), (2, 'Level 2: $500 - 35% ROI'), (3, 'Level 3: $1,000 - 40% ROI'), (4, 'Level 4: $3,000 - 50% ROI'), (5, 'Level 5: $5,000+ - 60% ROI')])),
                ('roi_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('daily_percentage', models.DecimalField(decimal_places=2, max_digits=10)),
                ('duration_seconds', models.IntegerField()),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roi_owners', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
