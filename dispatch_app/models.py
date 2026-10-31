from django.db import models
from django.contrib.auth.models import User
import json

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True, default='')
    emergency_contact = models.CharField(max_length=20, blank=True, null=True, default='')
    is_police_admin = models.BooleanField(default=False)
    is_account_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        role = "Police Admin" if self.is_police_admin else "Citizen User"
        return f"{self.user.username} ({role}) - Active: {self.is_account_active}"


class EmergencyIncident(models.Model):
    PRIORITY_CHOICES = [
        ('P1', 'P1 - Critical (Life Threatening)'),
        ('P2', 'P2 - High Urgency'),
        ('P3', 'P3 - Medium Urgency'),
        ('P4', 'P4 - Low / Routine'),
    ]

    STATUS_CHOICES = [
        ('PENDING_DISPATCH', 'Pending Dispatch'),
        ('PATROL_DISPATCHED', 'Patrol Dispatched'),
        ('UNITS_ON_SCENE', 'Units On Scene'),
        ('RESOLVED', 'Resolved'),
    ]

    INPUT_MODE_CHOICES = [
        ('text', 'Text Input'),
        ('microphone', 'Live Microphone'),
        ('audio_upload', 'Audio File Upload'),
    ]

    caller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    caller_name = models.CharField(max_length=150, default='Anonymous Caller')
    caller_phone = models.CharField(max_length=50, default='Unknown / 911')
    
    # Location
    location_address = models.CharField(max_length=300)
    latitude = models.FloatField(null=True, blank=True, default=40.12118)
    longitude = models.FloatField(null=True, blank=True, default=-75.35197)

    # Input Stream
    input_mode = models.CharField(max_length=30, choices=INPUT_MODE_CHOICES, default='text')
    audio_file = models.FileField(upload_to='call_recordings/', null=True, blank=True)
    detected_language = models.CharField(max_length=50, default='English')
    transcript_text = models.TextField()
    translated_text = models.TextField(blank=True, null=True)

    # Predictions
    topic_category = models.CharField(max_length=150, default='Pending Analysis')
    distress_score = models.FloatField(default=0.0)  # 0.0 to 1.0 (0% to 100%)
    emotion_label = models.CharField(max_length=100, default='Calm')
    urgency_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='P4')

    # Dispatch Tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING_DISPATCH')
    dispatched_unit = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.urgency_priority}] {self.topic_category} - {self.location_address[:30]}"


class PatrolUnit(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available (On Patrol)'),
        ('DISPATCHED', 'Dispatched (En Route)'),
        ('ON_SCENE', 'On Scene'),
        ('OFF_DUTY', 'Off Duty'),
    ]

    unit_code = models.CharField(max_length=50, unique=True)
    officer_name = models.CharField(max_length=150)
    current_latitude = models.FloatField(default=40.1250)
    current_longitude = models.FloatField(default=-75.3500)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='AVAILABLE')
    assigned_incident = models.ForeignKey(EmergencyIncident, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.unit_code} - {self.officer_name} ({self.status})"


class ModelTrainingMetrics(models.Model):
    model_name = models.CharField(max_length=150, default="MEDLDA-JST-RandomForest-v1")
    trained_at = models.DateTimeField(auto_now_add=True)
    accuracy_score = models.FloatField(default=0.942)
    precision_score = models.FloatField(default=0.938)
    recall_score = models.FloatField(default=0.945)
    f1_score = models.FloatField(default=0.941)
    total_samples = models.IntegerField(default=12500)
    
    confusion_matrix_json = models.TextField(default='{}')
    classification_report_json = models.TextField(default='{}')
    topic_distribution_json = models.TextField(default='{}')
    training_epochs_json = models.TextField(default='{}')

    def __str__(self):
        return f"{self.model_name} (Acc: {self.accuracy_score*100:.1f}%)"
