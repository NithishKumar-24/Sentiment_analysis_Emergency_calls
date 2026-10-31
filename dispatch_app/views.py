import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import UserProfile, EmergencyIncident, PatrolUnit, ModelTrainingMetrics
from .ml_engine.nlp_pipeline import emergency_ai
from .ml_engine.speech_processor import audio_processor

def is_admin_check(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.is_police_admin))

# ----------------- LANDING PAGE ----------------- #
def landing_home(request):
    total_incidents = EmergencyIncident.objects.count()
    critical_incidents = EmergencyIncident.objects.filter(urgency_priority__in=['P1', 'P2']).count()

    context = {
        'total_incidents': total_incidents,
        'critical_incidents': critical_incidents,
    }
    return render(request, 'landing_home.html', context)


# ----------------- AUTHENTICATION ----------------- #
def login_view(request):
    if request.user.is_authenticated:
        if is_admin_check(request.user):
            return redirect('police_dashboard')
        return redirect('user_dashboard')

    if request.method == 'POST':
        uname = request.POST.get('username', '').strip()
        pword = request.POST.get('password', '').strip()

        # Check default admin login override or authenticate
        user = authenticate(request, username=uname, password=pword)

        if user is not None:
            # Check if account is active in UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.is_account_active and not user.is_superuser:
                messages.error(request, 'Your account has been deactivated by the Police Admin. Contact support.')
                return render(request, 'auth/login.html')

            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')

            if is_admin_check(user):
                return redirect('police_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'auth/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        uname = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        pword = request.POST.get('password', '').strip()
        phone = request.POST.get('phone', '').strip()
        contact = request.POST.get('emergency_contact', '').strip()

        if User.objects.filter(username=uname).exists():
            messages.error(request, 'Username already exists. Please choose a different username.')
            return render(request, 'auth/register.html')

        user = User.objects.create_user(username=uname, email=email, password=pword)
        UserProfile.objects.create(
            user=user,
            phone_number=phone,
            emergency_contact=contact,
            is_police_admin=False,
            is_account_active=True
        )

        messages.success(request, 'Account created successfully! Please sign in.')
        return redirect('login')

    return render(request, 'auth/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out safely.')
    return redirect('login')


# ----------------- POLICE ADMIN DASHBOARD ----------------- #
@login_required
@user_passes_test(is_admin_check, login_url='login')
def police_dashboard(request):
    import json
    incidents = EmergencyIncident.objects.all().order_by('-created_at')
    users = User.objects.filter(is_superuser=False).select_related('profile')
    patrol_units = PatrolUnit.objects.all()

    # Metric counts
    p1_count = EmergencyIncident.objects.filter(urgency_priority='P1').count()
    p2_count = EmergencyIncident.objects.filter(urgency_priority='P2').count()
    pending_count = EmergencyIncident.objects.filter(status='PENDING_DISPATCH').count()

    incidents_data = []
    for inc in incidents:
        if inc.latitude is not None and inc.longitude is not None:
            incidents_data.append({
                'id': inc.id,
                'lat': float(inc.latitude),
                'lng': float(inc.longitude),
                'priority': inc.urgency_priority,
                'topic': inc.topic_category,
                'location': inc.location_address,
                'caller': inc.caller_name,
                'phone': inc.caller_phone,
                'distress': int(inc.distress_score * 100),
                'emotion': inc.emotion_label,
                'status': inc.status,
                'dispatched_unit': inc.dispatched_unit or '',
                'created_at': timezone.localtime(inc.created_at).strftime('%d %b %Y, %I:%M %p IST') if inc.created_at else ''
            })

    context = {
        'incidents': incidents,
        'users': users,
        'patrol_units': patrol_units,
        'p1_count': p1_count,
        'p2_count': p2_count,
        'pending_count': pending_count,
        'total_count': incidents.count(),
        'incidents_json': json.dumps(incidents_data),
    }
    return render(request, 'admin/police_dashboard.html', context)


# ----------------- ADMIN ACTIONS (USER MGMT & DISPATCH) ----------------- #
@login_required
@user_passes_test(is_admin_check, login_url='login')
def toggle_user_status(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser:
        messages.error(request, "Cannot modify superuser accounts.")
        return redirect('police_dashboard')

    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    profile.is_account_active = not profile.is_account_active
    profile.save()

    state = "Activated" if profile.is_account_active else "Deactivated"
    messages.success(request, f"User {target_user.username} account has been {state}.")
    return redirect('police_dashboard')


@login_required
@user_passes_test(is_admin_check, login_url='login')
def delete_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser:
        messages.error(request, "Cannot delete superuser accounts.")
    else:
        uname = target_user.username
        target_user.delete()
        messages.success(request, f"User {uname} has been deleted successfully.")
    return redirect('police_dashboard')


@login_required
@user_passes_test(is_admin_check, login_url='login')
def dispatch_patrol(request, incident_id):
    incident = get_object_or_404(EmergencyIncident, id=incident_id)
    unit_id = request.POST.get('unit_code')

    if unit_id:
        unit = PatrolUnit.objects.filter(unit_code=unit_id).first()
        if unit:
            unit.status = 'DISPATCHED'
            unit.assigned_incident = incident
            unit.save()
            incident.dispatched_unit = unit.unit_code
    else:
        # Find first available unit
        unit = PatrolUnit.objects.filter(status='AVAILABLE').first()
        if unit:
            unit.status = 'DISPATCHED'
            unit.assigned_incident = incident
            unit.save()
            incident.dispatched_unit = unit.unit_code
        else:
            incident.dispatched_unit = "HQ-DIRECT-DEPLOY"

    incident.status = 'PATROL_DISPATCHED'
    incident.save()
    messages.success(request, f"Unit {incident.dispatched_unit} dispatched to {incident.location_address}!")
    return redirect('police_dashboard')


@login_required
def api_active_alerts(request):
    """JSON API for real-time dashboard polling of incoming P1/P2 calls"""
    recent_p1 = EmergencyIncident.objects.filter(
        urgency_priority__in=['P1', 'P2'],
        status='PENDING_DISPATCH'
    )[:10]

    data = []
    for inc in recent_p1:
        data.append({
            'id': inc.id,
            'caller': inc.caller_name,
            'phone': inc.caller_phone,
            'location': inc.location_address,
            'lat': inc.latitude,
            'lng': inc.longitude,
            'topic': inc.topic_category,
            'distress_percent': int(inc.distress_score * 100),
            'priority': inc.urgency_priority,
            'time': timezone.localtime(inc.created_at).strftime("%I:%M:%S %p IST") if inc.created_at else '',
            'transcript': inc.transcript_text[:120]
        })
    return JsonResponse({'alerts': data, 'has_critical': len(data) > 0})


# ----------------- USER DASHBOARD ----------------- #
@login_required
def user_dashboard(request):
    user_incidents = EmergencyIncident.objects.filter(caller=request.user)
    context = {
        'incidents': user_incidents,
        'total_calls': user_incidents.count(),
    }
    return render(request, 'user/user_dashboard.html', context)


# ----------------- EMERGENCY PREDICTION PAGE ----------------- #
@login_required
def emergency_prediction(request):
    prediction_result = None

    if request.method == 'POST':
        location_address = request.POST.get('location', '').strip() or 'Unknown Location'
        lat = float(request.POST.get('latitude', 40.12118) or 40.12118)
        lng = float(request.POST.get('longitude', -75.35197) or -75.35197)
        input_mode = request.POST.get('input_mode', 'text')
        detected_language = request.POST.get('language', 'English')
        call_text = request.POST.get('call_text', '').strip()
        audio_file = request.FILES.get('audio_file')

        acoustic_boost = 0.0

        # Handle Audio File Upload
        saved_incident = EmergencyIncident(
            caller=request.user,
            caller_name=request.user.get_full_name() or request.user.username,
            caller_phone=getattr(request.user.profile, 'phone_number', '911'),
            location_address=location_address,
            latitude=lat,
            longitude=lng,
            input_mode=input_mode,
            detected_language=detected_language,
        )

        if audio_file:
            saved_incident.audio_file = audio_file
            saved_incident.save()  # saves to media/call_recordings/
            
            # Extract acoustic features
            features = audio_processor.extract_acoustic_features(saved_incident.audio_file.path)
            acoustic_boost = features.get('acoustic_boost', 0.0)

            # If user didn't type text, provide acoustic transcript approximation or user text
            if not call_text:
                call_text = f"Emergency voice transmission recorded ({features.get('stress_cue', 'voice cue')})."

        saved_incident.transcript_text = call_text

        # Auto-detect Telugu / Hindi script even if the dropdown was left on English
        detected_language = audio_processor.detect_language(call_text, detected_language)
        saved_incident.detected_language = detected_language

        # Multilingual Translation (Telugu / Hindi -> English)
        translated_text = call_text
        if detected_language in ['Telugu', 'Hindi', 'te', 'hi']:
            translated_text = audio_processor.translate_to_english(call_text, detected_language)
            saved_incident.translated_text = translated_text

        # Run Core ML Model (MEDLDA + JST + Urgency Scorer)
        analysis = emergency_ai.predict_full_incident(translated_text, acoustic_boost=acoustic_boost, original_text=call_text)

        # Save model predictions to DB
        saved_incident.topic_category = analysis['topic']
        saved_incident.distress_score = analysis['distress_score']
        saved_incident.emotion_label = analysis['emotion_label']
        saved_incident.urgency_priority = analysis['priority_code']
        saved_incident.status = 'PENDING_DISPATCH'
        saved_incident.save()

        prediction_result = {
            'incident': saved_incident,
            'analysis': analysis,
            'location': location_address,
            'coordinates': f"{lat:.5f}, {lng:.5f}",
            'detected_language': detected_language,
            'translated_text': translated_text if detected_language != 'English' else None,
            'is_critical': analysis['is_critical']
        }

        if analysis['is_critical']:
            messages.warning(request, f"HIGH URGENCY ALERT! Case classified as {analysis['priority_label']}. Relayed immediately to Police Command Dashboard.")
        else:
            messages.info(request, f"Incident logged. Priority Level: {analysis['priority_label']}.")

    return render(request, 'user/emergency_prediction.html', {'prediction': prediction_result})


# ----------------- MODEL TRAINING ANALYTICS PAGE ----------------- #
@login_required
def model_training_view(request):
    metrics = ModelTrainingMetrics.objects.first()
    
    conf_matrix = {}
    class_report = {}
    topic_dist = {}
    training_epochs = {}

    if metrics:
        try:
            conf_matrix = json.loads(metrics.confusion_matrix_json)
            class_report = json.loads(metrics.classification_report_json)
            topic_dist = json.loads(metrics.topic_distribution_json)
            training_epochs = json.loads(metrics.training_epochs_json)
        except Exception:
            pass

    context = {
        'metrics': metrics,
        'conf_matrix': conf_matrix,
        'class_report': class_report,
        'topic_dist': topic_dist,
        'training_epochs': training_epochs,
    }
    return render(request, 'user/model_training.html', context)
