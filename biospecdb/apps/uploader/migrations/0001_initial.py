# Generated by Django 4.2.1 on 2023-07-06 14:18

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BioSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sample_type', models.CharField(choices=[('PHARYNGEAL_SWAB', 'Pharyngeal Swab')], default='PHARYNGEAL_SWAB', max_length=128)),
                ('sample_processing', models.CharField(default='None', max_length=128)),
                ('freezing_time', models.IntegerField(blank=True, null=True)),
                ('thawing_time', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Disease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('description', models.CharField(max_length=256)),
                ('value_class', models.CharField(blank=True, choices=[('BOOL', 'Bool'), ('STR', 'Str'), ('INT', 'Int'), ('FLOAT', 'Float')], default='', max_length=128, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spectrometer', models.CharField(choices=[('AGILENT_COREY_630', 'Agilent Corey 630')], default='AGILENT_COREY_630', max_length=128)),
                ('atr_crystal', models.CharField(choices=[('ZNSE', 'Znse')], default='ZNSE', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('patient_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('gender', models.CharField(choices=[('MALE', 'Male'), ('FEMALE', 'Female')], max_length=8, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UploadedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='./biospecdb/apps/uploader/uploads/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_age', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(90)])),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visit', to='uploader.patient')),
                ('previous_visit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_visit', to='uploader.visit')),
            ],
        ),
        migrations.CreateModel(
            name='Symptom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('was_asked', models.BooleanField(default=True)),
                ('is_symptomatic', models.BooleanField(default=True)),
                ('days_symptomatic', models.IntegerField(blank=True, default=0, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('severity', models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('disease_value', models.CharField(blank=True, max_length=128, null=True)),
                ('disease', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='symptom', to='uploader.disease')),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='symptom', to='uploader.visit')),
            ],
        ),
        migrations.CreateModel(
            name='SpectralData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spectra_measurement', models.CharField(choices=[('ATR_FTIR', 'Atr Ftir')], default='ATR_FTIR', max_length=128)),
                ('acquisition_time', models.IntegerField(blank=True, null=True)),
                ('n_coadditions', models.IntegerField(default=32)),
                ('resolution', models.IntegerField(blank=True, null=True)),
                ('data', models.FileField(upload_to='uploads/')),
                ('bio_sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.biosample')),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spectral_data', to='uploader.instrument')),
            ],
        ),
        migrations.AddField(
            model_name='biosample',
            name='visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bio_sample', to='uploader.visit'),
        ),
    ]
