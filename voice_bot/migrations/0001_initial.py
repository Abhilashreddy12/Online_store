# Generated migration for VoiceBot models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VoiceQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(blank=True, max_length=100)),
                ('audio_file', models.FileField(blank=True, null=True, upload_to='voice_queries/%Y/%m/%d/')),
                ('audio_duration', models.FloatField(default=0, help_text='Duration in seconds')),
                ('transcribed_text', models.TextField()),
                ('detected_language', models.CharField(default='en', max_length=10)),
                ('intent', models.CharField(choices=[('ORDER_TRACKING', 'Order Tracking'), ('PRODUCT_SEARCH', 'Product Search'), ('PAYMENT_ISSUE', 'Payment Issue'), ('RETURN_REQUEST', 'Return Request'), ('GENERAL_QUERY', 'General Query'), ('UNKNOWN', 'Unknown Intent')], default='UNKNOWN', max_length=50)),
                ('confidence_score', models.FloatField(default=0.0)),
                ('confidence_level', models.CharField(choices=[('HIGH', 'High (>0.8)'), ('MEDIUM', 'Medium (0.5-0.8)'), ('LOW', 'Low (<0.5)')], default='MEDIUM', max_length=10)),
                ('response_message', models.TextField()),
                ('response_audio', models.FileField(blank=True, null=True, upload_to='voice_responses/%Y/%m/%d/')),
                ('error_message', models.TextField(blank=True)),
                ('processing_time_ms', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='voice_queries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Voice Query',
                'verbose_name_plural': 'Voice Queries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VoiceQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stt_model', models.CharField(default='whisper', max_length=50)),
                ('stt_model_size', models.CharField(default='base', max_length=20)),
                ('intent_classifier', models.CharField(default='rule_based', max_length=50)),
                ('intent_candidates', models.JSONField(default=dict)),
                ('raw_response', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('voice_query', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='log', to='voice_bot.voicequery')),
            ],
            options={
                'verbose_name': 'Voice Query Log',
                'verbose_name_plural': 'Voice Query Logs',
            },
        ),
        migrations.AddIndex(
            model_name='voicequery',
            index=models.Index(fields=['user', '-created_at'], name='voice_bot_v_user_id_012345_idx'),
        ),
        migrations.AddIndex(
            model_name='voicequery',
            index=models.Index(fields=['intent', 'created_at'], name='voice_bot_v_intent_012345_idx'),
        ),
        migrations.AddIndex(
            model_name='voicequery',
            index=models.Index(fields=['session_id'], name='voice_bot_v_session_012345_idx'),
        ),
    ]
