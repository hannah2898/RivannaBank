# Generated by Django 5.1.7 on 2025-04-12 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rivannabank', '0002_login'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(choices=[('Deposit', 'Deposit'), ('Withdrawal', 'Withdrawal'), ('E-Transfer', 'E-Transfer')], max_length=50),
        ),
    ]
