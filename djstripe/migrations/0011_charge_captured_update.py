from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations

import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0010_splitting_up_adds_from_alters'),
    ]

    operations = [
        migrations.AlterField(
            model_name='charge',
            name='captured',
            field=djstripe.fields.StripeBooleanField(
                help_text='If the charge was created without capturing, this boolean represents whether or not it is \
                still uncaptured or has since been captured.', default=False),
        ),
    ]
