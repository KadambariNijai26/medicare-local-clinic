from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import (
    UserProfile,
    Patient,
    Doctor,
    Appointment,
    MedicalRecord
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_profile(request):
    """
    Safely return the logged-in user's profile.
    """
    try:
        return request.user.profile
    except UserProfile.DoesNotExist:
        return None


def parse_date_value(value):
    """
    Convert YYYY-MM-DD string into a Python date object.
    Returns None if empty.
    Raises ValueError for invalid dates.
    """
    if not value:
        return None

    return date.fromisoformat(value)


def parse_time_value(value):
    """
    Convert HH:MM / HH:MM:SS string into a Python time object.
    Returns None if empty.
    Raises ValueError for invalid times.
    """
    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            '%H:%M'
        ).time()

    except ValueError:

        return datetime.strptime(
            value,
            '%H:%M:%S'
        ).time()


def user_is_admin(request):
    """
    Superuser or profile role admin.
    """
    if request.user.is_superuser:
        return True

    profile = get_user_profile(request)

    return profile is not None and profile.role == 'admin'


# ============================================================
# AUTHENTICATION
# ============================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        if not username or not password:

            messages.error(
                request,
                'Username and password are required.'
            )

            return redirect('login')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            # ------------------------------------------------
            # SUPERUSER
            # ------------------------------------------------

            if user.is_superuser:

                login(request, user)

                return redirect(
                    'admin_dashboard'
                )

            # ------------------------------------------------
            # PROFILE
            # ------------------------------------------------

            try:

                profile = user.profile

            except UserProfile.DoesNotExist:

                messages.error(
                    request,
                    'Your account profile was not found.'
                )

                return redirect('login')

            # ------------------------------------------------
            # APPROVAL
            # ------------------------------------------------

            if not profile.is_approved:

                messages.warning(
                    request,
                    'Your account is waiting for approval.'
                )

                return redirect('login')

            login(request, user)

            # ------------------------------------------------
            # ROLE REDIRECTION
            # ------------------------------------------------

            if profile.role == 'admin':

                return redirect(
                    'admin_dashboard'
                )

            elif profile.role == 'doctor':

                return redirect(
                    'doctor_dashboard'
                )

            elif profile.role == 'receptionist':

                return redirect(
                    'receptionist_dashboard'
                )

            elif profile.role == 'patient':

                return redirect(
                    'patient_dashboard'
                )

            messages.error(
                request,
                'Invalid user role.'
            )

            logout(request)

            return redirect('login')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(
        request,
        'accounts/login.html'
    )


def logout_view(request):

    logout(request)

    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return redirect('login')


# ============================================================
# DASHBOARD ROUTING
# ============================================================

@login_required
def dashboard(request):

    if request.user.is_superuser:

        return redirect(
            'admin_dashboard'
        )

    profile = get_user_profile(request)

    if profile is None:

        messages.error(
            request,
            'Your account profile was not found.'
        )

        return redirect('login')

    if not profile.is_approved:

        messages.warning(
            request,
            'Your account is waiting for approval.'
        )

        return redirect('login')

    if profile.role == 'admin':

        return redirect(
            'admin_dashboard'
        )

    elif profile.role == 'doctor':

        return redirect(
            'doctor_dashboard'
        )

    elif profile.role == 'receptionist':

        return redirect(
            'receptionist_dashboard'
        )

    elif profile.role == 'patient':

        return redirect(
            'patient_dashboard'
        )

    messages.error(
        request,
        'Invalid user role.'
    )

    return redirect('login')


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@login_required
def admin_dashboard(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to access the Admin Dashboard.'
            )

            return redirect('dashboard')

    pending_approvals_count = UserProfile.objects.filter(
        is_approved=False,
        role__in=[
            'patient',
            'doctor',
            'receptionist'
        ]
    ).count()

    total_receptionists = UserProfile.objects.filter(
        role='receptionist',
        is_approved=True
    ).count()

    receptionists = UserProfile.objects.filter(
        role='receptionist'
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    context = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'total_receptionists': total_receptionists,
        'receptionists': receptionists,
        'total_appointments': Appointment.objects.count(),
        'total_medical_records': MedicalRecord.objects.count(),
        'pending_approvals_count': pending_approvals_count,
    }

    return render(
        request,
        'accounts/admin_dashboard.html',
        context
    )


# ============================================================
# DOCTOR DASHBOARD
# ============================================================

@login_required
def doctor_dashboard(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access the Doctor Dashboard.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        doctor = None

    total_appointments = 0
    today_appointments = 0
    total_patients = 0
    total_medical_records = 0
    total_prescriptions = 0
    upcoming_appointments = []

    today = timezone.localdate()

    if doctor:

        total_appointments = Appointment.objects.filter(
            doctor=doctor
        ).count()

        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today
        ).count()

        total_patients = Appointment.objects.filter(
            doctor=doctor
        ).values(
            'patient'
        ).distinct().count()

        total_medical_records = MedicalRecord.objects.filter(
            doctor=doctor
        ).count()

        total_prescriptions = MedicalRecord.objects.filter(
            doctor=doctor
        ).exclude(
            prescription=''
        ).exclude(
            prescription__isnull=True
        ).count()

        upcoming_appointments = Appointment.objects.filter(
            doctor=doctor,
            status='scheduled',
            appointment_date__gte=today
        ).select_related(
            'patient__user'
        ).order_by(
            'appointment_date',
            'appointment_time'
        )[:5]

    context = {
        'doctor': doctor,
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'total_patients': total_patients,
        'my_patients': total_patients,
        'total_medical_records': total_medical_records,
        'total_prescriptions': total_prescriptions,
        'upcoming_appointments': upcoming_appointments,
    }

    return render(
        request,
        'accounts/doctor_dashboard.html',
        context
    )


# ============================================================
# DOCTOR APPOINTMENTS
# ============================================================

@login_required
def doctor_appointments(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        messages.error(
            request,
            'Doctor profile not found.'
        )

        return redirect('doctor_dashboard')

    appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related(
        'patient__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=search) |
            Q(patient__user__last_name__icontains=search) |
            Q(patient__user__username__icontains=search) |
            Q(status__icontains=search)
        )

    return render(
        request,
        'accounts/doctor_appointments.html',
        {
            'doctor': doctor,
            'appointments': appointments,
            'search': search,
        }
    )


# ============================================================
# RECEPTIONIST DASHBOARD
# ============================================================

@login_required
def receptionist_dashboard(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'receptionist':

            messages.error(
                request,
                'You are not authorized to access the Receptionist Dashboard.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    today = timezone.localdate()

    total_patients = Patient.objects.count()

    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).count()

    available_doctors = Doctor.objects.filter(
        is_available=True
    ).count()

    # Billing module has not been created yet.
    pending_bills = 0

    context = {
        'total_patients': total_patients,
        'today_appointments': today_appointments,
        'available_doctors': available_doctors,
        'pending_bills': pending_bills,
    }

    return render(
        request,
        'accounts/receptionist_dashboard.html',
        context
    )


# ============================================================
# PATIENT DASHBOARD
# ============================================================

@login_required
def patient_dashboard(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'patient':

            messages.error(
                request,
                'You are not authorized to access the Patient Dashboard.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        patient = request.user.patient

    except Patient.DoesNotExist:

        messages.error(
            request,
            'Patient profile not found.'
        )

        return redirect('dashboard')

    all_appointments = Appointment.objects.filter(
        patient=patient
    ).select_related(
        'doctor__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    all_medical_records = MedicalRecord.objects.filter(
        patient=patient
    ).select_related(
        'doctor__user',
        'appointment'
    ).order_by(
        '-record_date',
        '-id'
    )

    total_appointments = all_appointments.count()

    total_medical_records = all_medical_records.count()

    total_prescriptions = all_medical_records.exclude(
        prescription=''
    ).exclude(
        prescription__isnull=True
    ).count()

    today = timezone.localdate()

    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        status='scheduled',
        appointment_date__gte=today
    ).select_related(
        'doctor__user'
    ).order_by(
        'appointment_date',
        'appointment_time'
    )[:5]

    context = {
        'patient': patient,
        'appointments': all_appointments[:5],
        'medical_records': all_medical_records[:5],
        'upcoming_appointments': upcoming_appointments,
        'total_appointments': total_appointments,
        'total_medical_records': total_medical_records,
        'total_prescriptions': total_prescriptions,
    }

    return render(
        request,
        'accounts/patient_dashboard.html',
        context
    )


# ============================================================
# PATIENT APPOINTMENTS
# ============================================================

@login_required
def patient_appointments(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'patient':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        patient = request.user.patient

    except Patient.DoesNotExist:

        messages.error(
            request,
            'Patient profile not found.'
        )

        return redirect('patient_dashboard')

    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related(
        'doctor__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    return render(
        request,
        'accounts/patient_appointments.html',
        {
            'patient': patient,
            'appointments': appointments,
        }
    )


# ============================================================
# PATIENT MEDICAL RECORDS
# ============================================================

@login_required
def patient_medical_records(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'patient':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        patient = request.user.patient

    except Patient.DoesNotExist:

        messages.error(
            request,
            'Patient profile not found.'
        )

        return redirect('patient_dashboard')

    medical_records = MedicalRecord.objects.filter(
        patient=patient
    ).select_related(
        'doctor__user',
        'appointment'
    ).order_by(
        '-record_date',
        '-id'
    )

    return render(
        request,
        'accounts/patient_medical_records.html',
        {
            'patient': patient,
            'medical_records': medical_records,
            'total_records': medical_records.count(),
        }
    )


# ============================================================
# PATIENT MANAGEMENT
# ============================================================

@login_required
def patient_list(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to view patients.'
            )

            return redirect('dashboard')

    patients = Patient.objects.select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        patients = patients.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(phone__icontains=search)
        )

    return render(
        request,
        'accounts/patient_list.html',
        {
            'patients': patients,
            'search': search,
        }
    )


@login_required
def pending_approvals(request):

    if not user_is_admin(request):

        messages.error(
            request,
            'You are not authorized to view pending approvals.'
        )

        return redirect('dashboard')

    pending_profiles = UserProfile.objects.filter(
        is_approved=False,
        role__in=['patient', 'doctor', 'receptionist']
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'accounts/pending_approvals.html',
        {
            'pending_profiles': pending_profiles,
        }
    )


@login_required
def approve_account(request, user_id):

    if not user_is_admin(request):

        messages.error(
            request,
            'You are not authorized to approve accounts.'
        )

        return redirect('dashboard')

    user = get_object_or_404(
        User,
        id=user_id
    )

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        messages.error(
            request,
            'User profile was not found.'
        )
        return redirect('pending_approvals')

    if profile.role not in ['patient', 'doctor', 'receptionist']:
        messages.error(
            request,
            'This account cannot be approved from here.'
        )
        return redirect('pending_approvals')

    profile.is_approved = True
    profile.save()

    role_name = profile.get_role_display()
    full_name = user.get_full_name() or user.username

    messages.success(
        request,
        f'{role_name} {full_name} has been approved successfully.'
    )

    return redirect('pending_approvals')


@login_required
def add_patient(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to add patients.'
            )

            return redirect('dashboard')

    if request.method == 'POST':

        # ----------------------------------------------------
        # ACCOUNT INFORMATION
        # ----------------------------------------------------

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        email = request.POST.get(
            'email',
            ''
        ).strip()

        # ----------------------------------------------------
        # PERSONAL INFORMATION
        # ----------------------------------------------------

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        date_of_birth = request.POST.get(
            'date_of_birth',
            ''
        ).strip()

        gender = request.POST.get(
            'gender',
            ''
        ).strip()

        # ----------------------------------------------------
        # CONTACT INFORMATION
        # ----------------------------------------------------

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        emergency_contact = request.POST.get(
            'emergency_contact',
            ''
        ).strip()

        address = request.POST.get(
            'address',
            ''
        ).strip()

        # ----------------------------------------------------
        # MEDICAL INFORMATION
        # ----------------------------------------------------

        blood_group = request.POST.get(
            'blood_group',
            ''
        ).strip()

        medical_history = request.POST.get(
            'medical_history',
            ''
        ).strip()

        # ----------------------------------------------------
        # REQUIRED FIELD VALIDATION
        # ----------------------------------------------------

        if not username:

            messages.error(
                request,
                'Username is required.'
            )

            return redirect('add_patient')

        if not password:

            messages.error(
                request,
                'Password is required.'
            )

            return redirect('add_patient')

        if not confirm_password:

            messages.error(
                request,
                'Please confirm the password.'
            )

            return redirect('add_patient')

        if not first_name:

            messages.error(
                request,
                'First name is required.'
            )

            return redirect('add_patient')

        # ----------------------------------------------------
        # PASSWORD CONFIRMATION
        # ----------------------------------------------------

        if password != confirm_password:

            messages.error(
                request,
                'Passwords do not match.'
            )

            return redirect('add_patient')

        # ----------------------------------------------------
        # USERNAME VALIDATION
        # ----------------------------------------------------

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                'Username already exists.'
            )

            return redirect('add_patient')

        # ----------------------------------------------------
        # DATE OF BIRTH VALIDATION
        # ----------------------------------------------------

        dob_value = None

        if date_of_birth:

            try:

                dob_value = parse_date_value(
                    date_of_birth
                )

            except ValueError:

                messages.error(
                    request,
                    'Please enter a valid date of birth.'
                )

                return redirect('add_patient')

        # ----------------------------------------------------
        # GENDER VALIDATION
        # ----------------------------------------------------

        valid_genders = [
            choice[0]
            for choice in Patient.GENDER_CHOICES
        ]

        if gender and gender not in valid_genders:

            messages.error(
                request,
                'Please select a valid gender.'
            )

            return redirect('add_patient')

        # ----------------------------------------------------
        # BLOOD GROUP VALIDATION
        # ----------------------------------------------------

        valid_blood_groups = [
            choice[0]
            for choice in Patient.BLOOD_GROUP_CHOICES
        ]

        if blood_group and blood_group not in valid_blood_groups:

            messages.error(
                request,
                'Please select a valid blood group.'
            )

            return redirect('add_patient')

        # ----------------------------------------------------
        # CREATE USER ACCOUNT
        # ----------------------------------------------------

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        # ----------------------------------------------------
        # CREATE USER PROFILE
        # ----------------------------------------------------

        UserProfile.objects.create(
            user=user,
            role='patient',
            phone=phone,
            is_approved=True
        )

        # ----------------------------------------------------
        # CREATE PATIENT PROFILE
        # ----------------------------------------------------

        Patient.objects.create(
            user=user,
            date_of_birth=dob_value,
            gender=gender,
            phone=phone,
            address=address,
            blood_group=blood_group,
            emergency_contact=emergency_contact,
            medical_history=medical_history
        )

        messages.success(
            request,
            'Patient added successfully.'
        )

        return redirect(
            'patient_list'
        )

    return render(
        request,
        'accounts/add_patient.html'
    )


@login_required
def edit_patient(request, patient_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to edit patients.'
            )

            return redirect('dashboard')

    patient = get_object_or_404(
        Patient,
        id=patient_id
    )

    user = patient.user

    if request.method == 'POST':

        date_of_birth = request.POST.get(
            'date_of_birth',
            ''
        ).strip()

        dob_value = None

        if date_of_birth:

            try:

                dob_value = parse_date_value(
                    date_of_birth
                )

            except ValueError:

                messages.error(
                    request,
                    'Please enter a valid date of birth.'
                )

                return redirect(
                    'edit_patient',
                    patient_id=patient.id
                )

        user.first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        user.last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        user.email = request.POST.get(
            'email',
            ''
        ).strip()

        user.save()

        patient.date_of_birth = dob_value

        patient.gender = request.POST.get(
            'gender',
            ''
        ).strip()

        patient.phone = request.POST.get(
            'phone',
            ''
        ).strip()

        patient.address = request.POST.get(
            'address',
            ''
        ).strip()

        patient.blood_group = request.POST.get(
            'blood_group',
            ''
        ).strip()

        patient.emergency_contact = request.POST.get(
            'emergency_contact',
            ''
        ).strip()

        patient.medical_history = request.POST.get(
            'medical_history',
            ''
        ).strip()

        patient.save()

        try:

            profile = user.profile

            profile.phone = patient.phone

            profile.save()

        except UserProfile.DoesNotExist:
            pass

        messages.success(
            request,
            'Patient updated successfully.'
        )

        return redirect('patient_list')

    return render(
        request,
        'accounts/edit_patient.html',
        {
            'patient': patient
        }
    )


@login_required
def delete_patient(request, patient_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to delete patients.'
            )

            return redirect('dashboard')

    patient = get_object_or_404(
        Patient,
        id=patient_id
    )

    if request.method == 'POST':

        user = patient.user

        patient.delete()
        user.delete()

        messages.success(
            request,
            'Patient deleted successfully.'
        )

        return redirect('patient_list')

    return render(
        request,
        'accounts/delete_patient.html',
        {
            'patient': patient
        }
    )


# ============================================================
# DOCTOR MANAGEMENT
# ============================================================

@login_required
def doctor_list(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to view doctors.'
            )

            return redirect('dashboard')

    doctors = Doctor.objects.select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        doctors = doctors.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(specialization__icontains=search)
        )

    return render(
        request,
        'accounts/doctor_list.html',
        {
            'doctors': doctors,
            'search': search,
        }
    )



# ============================================================
# RECEPTIONIST MANAGEMENT
# ============================================================

@login_required
def receptionist_list(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to view receptionists.'
            )

            return redirect('dashboard')

    receptionists = UserProfile.objects.filter(
        role='receptionist'
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        receptionists = receptionists.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search)
        )

    return render(
        request,
        'accounts/receptionist_list.html',
        {
            'receptionists': receptionists,
            'search': search,
        }
    )


@login_required
def add_receptionist(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to add receptionists.'
            )

            return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not username:
            messages.error(request, 'Username is required.')
            return redirect('add_receptionist')

        if not password:
            messages.error(request, 'Password is required.')
            return redirect('add_receptionist')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('add_receptionist')

        if not first_name:
            messages.error(request, 'First name is required.')
            return redirect('add_receptionist')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('add_receptionist')

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        UserProfile.objects.create(
            user=user,
            role='receptionist',
            phone=phone,
            is_approved=True
        )

        messages.success(
            request,
            'Receptionist added successfully.'
        )

        return redirect('receptionist_list')

    return render(
        request,
        'accounts/add_receptionist.html'
    )

@login_required
def add_doctor(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to add doctors.'
            )

            return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        specialization = request.POST.get(
            'specialization',
            ''
        ).strip()

        qualification = request.POST.get(
            'qualification',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        experience = request.POST.get(
            'experience',
            '0'
        ).strip()

        consultation_fee = request.POST.get(
            'consultation_fee',
            '0'
        ).strip()

        available_days = request.POST.get(
            'available_days',
            ''
        ).strip()

        is_available = request.POST.get(
            'is_available'
        ) == 'on'

        if not username or not password:

            messages.error(
                request,
                'Username and password are required.'
            )

            return redirect('add_doctor')

        if not qualification:

            messages.error(
                request,
                'Qualification is required.'
            )

            return redirect('add_doctor')

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                'Username already exists.'
            )

            return redirect('add_doctor')

        try:

            experience_value = int(
                experience or 0
            )

            if experience_value < 0:
                raise ValueError

        except ValueError:

            messages.error(
                request,
                'Experience must be a valid positive number.'
            )

            return redirect('add_doctor')

        try:

            fee_value = Decimal(
                consultation_fee or '0'
            )

            if fee_value < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):

            messages.error(
                request,
                'Consultation fee must be a valid amount.'
            )

            return redirect('add_doctor')

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        UserProfile.objects.create(
            user=user,
            role='doctor',
            phone=phone,
            is_approved=True
        )

        Doctor.objects.create(
            user=user,
            specialization=specialization or 'general',
            qualification=qualification,
            phone=phone,
            experience=experience_value,
            consultation_fee=fee_value,
            available_days=available_days,
            is_available=is_available
        )

        messages.success(
            request,
            'Doctor added successfully.'
        )

        return redirect('doctor_list')

    return render(
        request,
        'accounts/add_doctor.html'
    )


@login_required
def edit_doctor(request, doctor_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to edit doctors.'
            )

            return redirect('dashboard')

    doctor = get_object_or_404(
        Doctor,
        id=doctor_id
    )

    user = doctor.user

    if request.method == 'POST':

        experience = request.POST.get(
            'experience',
            '0'
        ).strip()

        consultation_fee = request.POST.get(
            'consultation_fee',
            '0'
        ).strip()

        qualification = request.POST.get(
            'qualification',
            ''
        ).strip()

        if not qualification:

            messages.error(
                request,
                'Qualification is required.'
            )

            return redirect(
                'edit_doctor',
                doctor_id=doctor.id
            )

        try:

            experience_value = int(
                experience or 0
            )

            if experience_value < 0:
                raise ValueError

        except ValueError:

            messages.error(
                request,
                'Experience must be a valid positive number.'
            )

            return redirect(
                'edit_doctor',
                doctor_id=doctor.id
            )

        try:

            fee_value = Decimal(
                consultation_fee or '0'
            )

            if fee_value < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError):

            messages.error(
                request,
                'Consultation fee must be a valid amount.'
            )

            return redirect(
                'edit_doctor',
                doctor_id=doctor.id
            )

        user.first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        user.last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        user.email = request.POST.get(
            'email',
            ''
        ).strip()

        user.save()

        doctor.specialization = request.POST.get(
            'specialization',
            ''
        ) or 'general'

        doctor.qualification = qualification

        doctor.phone = request.POST.get(
            'phone',
            ''
        ).strip()

        doctor.experience = experience_value

        doctor.consultation_fee = fee_value

        doctor.available_days = request.POST.get(
            'available_days',
            ''
        ).strip()

        doctor.is_available = request.POST.get(
            'is_available'
        ) == 'on'

        doctor.save()

        try:

            profile = user.profile

            profile.phone = doctor.phone

            profile.save()

        except UserProfile.DoesNotExist:
            pass

        messages.success(
            request,
            'Doctor updated successfully.'
        )

        return redirect('doctor_list')

    return render(
        request,
        'accounts/edit_doctor.html',
        {
            'doctor': doctor
        }
    )


@login_required
def delete_doctor(request, doctor_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to delete doctors.'
            )

            return redirect('dashboard')

    doctor = get_object_or_404(
        Doctor,
        id=doctor_id
    )

    if request.method == 'POST':

        user = doctor.user

        doctor.delete()
        user.delete()

        messages.success(
            request,
            'Doctor deleted successfully.'
        )

        return redirect('doctor_list')

    return render(
        request,
        'accounts/delete_doctor.html',
        {
            'doctor': doctor
        }
    )


# ============================================================
# APPOINTMENT MANAGEMENT
# ============================================================

@login_required
def appointment_list(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to view appointments.'
            )

            return redirect('dashboard')

    appointments = Appointment.objects.select_related(
        'patient__user',
        'doctor__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=search) |
            Q(patient__user__last_name__icontains=search) |
            Q(patient__user__username__icontains=search) |
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search) |
            Q(doctor__user__username__icontains=search) |
            Q(doctor__specialization__icontains=search) |
            Q(status__icontains=search)
        )

    return render(
        request,
        'accounts/appointment_list.html',
        {
            'appointments': appointments,
            'search': search,
            'search_query': search,
        }
    )


@login_required
def add_appointment(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to add appointments.'
            )

            return redirect('dashboard')

    patients = Patient.objects.select_related(
        'user'
    ).order_by(
        'user__first_name',
        'user__last_name'
    )

    doctors = Doctor.objects.select_related(
        'user'
    ).filter(
        is_available=True
    ).order_by(
        'user__first_name',
        'user__last_name'
    )

    if request.method == 'POST':

        patient_id = request.POST.get(
            'patient'
        )

        doctor_id = request.POST.get(
            'doctor'
        )

        appointment_date = request.POST.get(
            'appointment_date'
        )

        appointment_time = request.POST.get(
            'appointment_time'
        )

        reason = request.POST.get(
            'reason',
            ''
        ).strip()

        status = request.POST.get(
            'status'
        ) or 'scheduled'

        notes = request.POST.get(
            'notes',
            ''
        ).strip()

        if not patient_id:

            messages.error(
                request,
                'Please select a patient.'
            )

            return redirect('add_appointment')

        if not doctor_id:

            messages.error(
                request,
                'Please select a doctor.'
            )

            return redirect('add_appointment')

        if not appointment_date:

            messages.error(
                request,
                'Appointment date is required.'
            )

            return redirect('add_appointment')

        if not appointment_time:

            messages.error(
                request,
                'Appointment time is required.'
            )

            return redirect('add_appointment')

        valid_statuses = dict(
            Appointment.STATUS_CHOICES
        )

        if status not in valid_statuses:

            messages.error(
                request,
                'Invalid appointment status.'
            )

            return redirect('add_appointment')

        try:

            appointment_date_value = parse_date_value(
                appointment_date
            )

        except ValueError:

            messages.error(
                request,
                'Please enter a valid appointment date.'
            )

            return redirect('add_appointment')

        try:

            appointment_time_value = parse_time_value(
                appointment_time
            )

        except ValueError:

            messages.error(
                request,
                'Please enter a valid appointment time.'
            )

            return redirect('add_appointment')

        patient = get_object_or_404(
            Patient,
            id=patient_id
        )

        doctor = get_object_or_404(
            Doctor,
            id=doctor_id
        )

        if not doctor.is_available:

            messages.error(
                request,
                'The selected doctor is currently unavailable.'
            )

            return redirect('add_appointment')

        if status == 'scheduled':

            already_booked = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date_value,
                appointment_time=appointment_time_value,
                status='scheduled'
            ).exists()

            if already_booked:

                messages.error(
                    request,
                    'This doctor already has a scheduled appointment at the selected date and time.'
                )

                return redirect('add_appointment')

        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date_value,
            appointment_time=appointment_time_value,
            reason=reason,
            status=status,
            notes=notes
        )

        messages.success(
            request,
            'Appointment added successfully.'
        )

        return redirect('appointment_list')

    return render(
        request,
        'accounts/add_appointment.html',
        {
            'patients': patients,
            'doctors': doctors,
        }
    )


@login_required
def edit_appointment(request, appointment_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to edit appointments.'
            )

            return redirect('dashboard')

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            'patient__user',
            'doctor__user'
        ),
        id=appointment_id
    )

    patients = Patient.objects.select_related(
        'user'
    ).order_by(
        'user__first_name',
        'user__last_name'
    )

    doctors = Doctor.objects.select_related(
        'user'
    ).order_by(
        'user__first_name',
        'user__last_name'
    )

    if request.method == 'POST':

        patient_id = request.POST.get(
            'patient'
        )

        doctor_id = request.POST.get(
            'doctor'
        )

        appointment_date = request.POST.get(
            'appointment_date'
        )

        appointment_time = request.POST.get(
            'appointment_time'
        )

        reason = request.POST.get(
            'reason',
            ''
        ).strip()

        status = request.POST.get(
            'status'
        ) or 'scheduled'

        notes = request.POST.get(
            'notes',
            ''
        ).strip()

        if not patient_id:

            messages.error(
                request,
                'Please select a patient.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        if not doctor_id:

            messages.error(
                request,
                'Please select a doctor.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        if not appointment_date:

            messages.error(
                request,
                'Appointment date is required.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        if not appointment_time:

            messages.error(
                request,
                'Appointment time is required.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        valid_statuses = dict(
            Appointment.STATUS_CHOICES
        )

        if status not in valid_statuses:

            messages.error(
                request,
                'Invalid appointment status.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        try:

            appointment_date_value = parse_date_value(
                appointment_date
            )

        except ValueError:

            messages.error(
                request,
                'Please enter a valid appointment date.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        try:

            appointment_time_value = parse_time_value(
                appointment_time
            )

        except ValueError:

            messages.error(
                request,
                'Please enter a valid appointment time.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        patient = get_object_or_404(
            Patient,
            id=patient_id
        )

        doctor = get_object_or_404(
            Doctor,
            id=doctor_id
        )

        if (
            not doctor.is_available
            and doctor.id != appointment.doctor_id
        ):

            messages.error(
                request,
                'The selected doctor is currently unavailable.'
            )

            return redirect(
                'edit_appointment',
                appointment_id=appointment.id
            )

        if status == 'scheduled':

            already_booked = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date_value,
                appointment_time=appointment_time_value,
                status='scheduled'
            ).exclude(
                id=appointment.id
            ).exists()

            if already_booked:

                messages.error(
                    request,
                    'This doctor already has a scheduled appointment at the selected date and time.'
                )

                return redirect(
                    'edit_appointment',
                    appointment_id=appointment.id
                )

        appointment.patient = patient
        appointment.doctor = doctor
        appointment.appointment_date = appointment_date_value
        appointment.appointment_time = appointment_time_value
        appointment.reason = reason
        appointment.status = status
        appointment.notes = notes

        appointment.save()

        messages.success(
            request,
            'Appointment updated successfully.'
        )

        return redirect('appointment_list')

    return render(
        request,
        'accounts/edit_appointment.html',
        {
            'appointment': appointment,
            'patients': patients,
            'doctors': doctors,
        }
    )


@login_required
def delete_appointment(request, appointment_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role != 'admin':

            messages.error(
                request,
                'You are not authorized to delete appointments.'
            )

            return redirect('dashboard')

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id
    )

    if request.method == 'POST':

        appointment.delete()

        messages.success(
            request,
            'Appointment deleted successfully.'
        )

        return redirect('appointment_list')

    return render(
        request,
        'accounts/delete_appointment.html',
        {
            'appointment': appointment
        }
    )


# ============================================================
# MEDICAL RECORD MANAGEMENT
# ============================================================

@login_required
def medical_record_list(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'doctor',
            'receptionist'
        ]:

            messages.error(
                request,
                'You are not authorized to view medical records.'
            )

            return redirect('dashboard')

    records = MedicalRecord.objects.select_related(
        'patient__user',
        'doctor__user',
        'appointment'
    ).order_by(
        '-record_date',
        '-id'
    )

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile and profile.role == 'doctor':

            try:

                doctor = request.user.doctor

                records = records.filter(
                    doctor=doctor
                )

            except Doctor.DoesNotExist:

                records = records.none()

    search = request.GET.get(
        'search',
        ''
    ).strip()

    if search:

        records = records.filter(
            Q(patient__user__first_name__icontains=search) |
            Q(patient__user__last_name__icontains=search) |
            Q(patient__user__username__icontains=search) |
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search) |
            Q(diagnosis__icontains=search) |
            Q(symptoms__icontains=search)
        )

    return render(
        request,
        'accounts/medical_record_list.html',
        {
            'records': records,
            'search': search,
        }
    )


@login_required
def add_medical_record(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'doctor'
        ]:

            messages.error(
                request,
                'You are not authorized to add medical records.'
            )

            return redirect('dashboard')

        if profile.role == 'doctor' and not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    patients = Patient.objects.select_related(
        'user'
    ).order_by(
        'user__first_name'
    )

    doctors = Doctor.objects.select_related(
        'user'
    ).filter(
        is_available=True
    ).order_by(
        'user__first_name'
    )

    appointments = Appointment.objects.select_related(
        'patient__user',
        'doctor__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    profile = get_user_profile(request)

    if (
        not request.user.is_superuser
        and profile
        and profile.role == 'doctor'
    ):

        try:

            doctor = request.user.doctor

            doctors = doctors.filter(
                id=doctor.id
            )

            appointments = appointments.filter(
                doctor=doctor
            )

        except Doctor.DoesNotExist:

            doctors = doctors.none()
            appointments = appointments.none()

    if request.method == 'POST':

        patient_id = request.POST.get(
            'patient'
        )

        doctor_id = request.POST.get(
            'doctor'
        )

        appointment_id = request.POST.get(
            'appointment'
        )

        diagnosis = request.POST.get(
            'diagnosis',
            ''
        ).strip()

        symptoms = request.POST.get(
            'symptoms',
            ''
        ).strip()

        prescription = request.POST.get(
            'prescription',
            ''
        ).strip()

        treatment = request.POST.get(
            'treatment',
            ''
        ).strip()

        notes = request.POST.get(
            'notes',
            ''
        ).strip()

        if not patient_id or not doctor_id or not diagnosis:

            messages.error(
                request,
                'Patient, doctor and diagnosis are required.'
            )

            return redirect(
                'add_medical_record'
            )

        patient = get_object_or_404(
            Patient,
            id=patient_id
        )

        doctor = get_object_or_404(
            Doctor,
            id=doctor_id
        )

        if (
            not request.user.is_superuser
            and profile
            and profile.role == 'doctor'
        ):

            if doctor.user != request.user:

                messages.error(
                    request,
                    'You can only create medical records for yourself.'
                )

                return redirect(
                    'add_medical_record'
                )

        appointment = None

        if appointment_id:

            appointment = get_object_or_404(
                Appointment,
                id=appointment_id
            )

            if (
                appointment.patient_id != patient.id
                or appointment.doctor_id != doctor.id
            ):

                messages.error(
                    request,
                    'Selected appointment does not belong to the selected patient and doctor.'
                )

                return redirect(
                    'add_medical_record'
                )

        MedicalRecord.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            diagnosis=diagnosis,
            symptoms=symptoms,
            prescription=prescription,
            treatment=treatment,
            notes=notes
        )

        messages.success(
            request,
            'Medical record added successfully.'
        )

        return redirect(
            'medical_record_list'
        )

    return render(
        request,
        'accounts/add_medical_record.html',
        {
            'patients': patients,
            'doctors': doctors,
            'appointments': appointments,
        }
    )


@login_required
def edit_medical_record(request, record_id):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:
            return redirect('dashboard')

        if profile.role not in [
            'admin',
            'doctor'
        ]:

            messages.error(
                request,
                'You are not authorized to edit medical records.'
            )

            return redirect('dashboard')

        if profile.role == 'doctor' and not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    record = get_object_or_404(
        MedicalRecord,
        id=record_id
    )

    profile = get_user_profile(request)

    if (
        not request.user.is_superuser
        and profile
        and profile.role == 'doctor'
    ):

        try:

            doctor = request.user.doctor

            if record.doctor != doctor:

                messages.error(
                    request,
                    'You can only edit your own medical records.'
                )

                return redirect(
                    'doctor_medical_records'
                )

        except Doctor.DoesNotExist:

            messages.error(
                request,
                'Doctor profile not found.'
            )

            return redirect(
                'doctor_dashboard'
            )

    patients = Patient.objects.select_related(
        'user'
    ).order_by(
        'user__first_name'
    )

    doctors = Doctor.objects.select_related(
        'user'
    ).order_by(
        'user__first_name'
    )

    appointments = Appointment.objects.select_related(
        'patient__user',
        'doctor__user'
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    if (
        not request.user.is_superuser
        and profile
        and profile.role == 'doctor'
    ):

        try:

            doctors = doctors.filter(
                id=request.user.doctor.id
            )

            appointments = appointments.filter(
                doctor=request.user.doctor
            )

        except Doctor.DoesNotExist:

            doctors = doctors.none()
            appointments = appointments.none()

    if request.method == 'POST':

        patient_id = request.POST.get(
            'patient'
        )

        doctor_id = request.POST.get(
            'doctor'
        )

        if not patient_id or not doctor_id:

            messages.error(
                request,
                'Patient and doctor are required.'
            )

            return redirect(
                'edit_medical_record',
                record_id=record.id
            )

        patient = get_object_or_404(
            Patient,
            id=patient_id
        )

        doctor = get_object_or_404(
            Doctor,
            id=doctor_id
        )

        if (
            not request.user.is_superuser
            and profile
            and profile.role == 'doctor'
        ):

            if doctor.user != request.user:

                messages.error(
                    request,
                    'You can only keep your own doctor profile on this record.'
                )

                return redirect(
                    'medical_record_list'
                )

        diagnosis = request.POST.get(
            'diagnosis',
            ''
        ).strip()

        if not diagnosis:

            messages.error(
                request,
                'Diagnosis is required.'
            )

            return redirect(
                'edit_medical_record',
                record_id=record.id
            )

        appointment_id = request.POST.get(
            'appointment'
        )

        appointment = None

        if appointment_id:

            appointment = get_object_or_404(
                Appointment,
                id=appointment_id
            )

            if (
                appointment.patient_id != patient.id
                or appointment.doctor_id != doctor.id
            ):

                messages.error(
                    request,
                    'Selected appointment does not belong to the selected patient and doctor.'
                )

                return redirect(
                    'edit_medical_record',
                    record_id=record.id
                )

        record.patient = patient
        record.doctor = doctor
        record.appointment = appointment

        record.diagnosis = diagnosis

        record.symptoms = request.POST.get(
            'symptoms',
            ''
        ).strip()

        record.prescription = request.POST.get(
            'prescription',
            ''
        ).strip()

        record.treatment = request.POST.get(
            'treatment',
            ''
        ).strip()

        record.notes = request.POST.get(
            'notes',
            ''
        ).strip()

        record.save()

        messages.success(
            request,
            'Medical record updated successfully.'
        )

        return redirect(
            'medical_record_list'
        )

    return render(
        request,
        'accounts/edit_medical_record.html',
        {
            'record': record,
            'patients': patients,
            'doctors': doctors,
            'appointments': appointments,
        }
    )


# ============================================================
# DELETE MEDICAL RECORD
# ============================================================

@login_required
def delete_medical_record(request, record_id):

    record = get_object_or_404(
        MedicalRecord.objects.select_related(
            'patient__user',
            'doctor__user'
        ),
        id=record_id
    )

    # --------------------------------------------------------
    # SUPERUSER
    # --------------------------------------------------------

    if request.user.is_superuser:

        if request.method == 'POST':

            record.delete()

            messages.success(
                request,
                'Medical record deleted successfully.'
            )

            return redirect(
                'medical_record_list'
            )

        return render(
            request,
            'accounts/delete_medical_record.html',
            {
                'record': record
            }
        )

    # --------------------------------------------------------
    # PROFILE CHECK
    # --------------------------------------------------------

    profile = get_user_profile(request)

    if profile is None:

        messages.error(
            request,
            'Profile not found.'
        )

        return redirect('dashboard')

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if profile.role == 'admin':

        if request.method == 'POST':

            record.delete()

            messages.success(
                request,
                'Medical record deleted successfully.'
            )

            return redirect(
                'medical_record_list'
            )

        return render(
            request,
            'accounts/delete_medical_record.html',
            {
                'record': record
            }
        )

    # --------------------------------------------------------
    # DOCTOR
    # --------------------------------------------------------

    if profile.role == 'doctor':

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

        try:

            doctor = request.user.doctor

        except Doctor.DoesNotExist:

            messages.error(
                request,
                'Doctor profile not found.'
            )

            return redirect(
                'doctor_dashboard'
            )

        if record.doctor != doctor:

            messages.error(
                request,
                'You are not authorized to delete this medical record.'
            )

            return redirect(
                'doctor_medical_records'
            )

        if request.method == 'POST':

            patient_id = record.patient.id

            record.delete()

            messages.success(
                request,
                'Medical record deleted successfully.'
            )

            return redirect(
                'doctor_patient_medical_records',
                patient_id=patient_id
            )

        return render(
            request,
            'accounts/delete_medical_record.html',
            {
                'record': record
            }
        )

    # --------------------------------------------------------
    # OTHER ROLES
    # --------------------------------------------------------

    messages.error(
        request,
        'You are not authorized to delete medical records.'
    )

    return redirect('dashboard')


# ============================================================
# DOCTOR PATIENTS
# ============================================================

@login_required
def doctor_patients(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Doctor profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        messages.error(
            request,
            'Doctor profile not found.'
        )

        return redirect(
            'doctor_dashboard'
        )

    patients = Patient.objects.filter(
        appointments__doctor=doctor
    ).select_related(
        'user'
    ).distinct().order_by(
        'user__first_name',
        'user__last_name'
    )

    return render(
        request,
        'accounts/doctor_patients.html',
        {
            'doctor': doctor,
            'patients': patients,
        }
    )


# ============================================================
# DOCTOR MEDICAL RECORDS
# ============================================================

@login_required
def doctor_medical_records(request):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Doctor profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        messages.error(
            request,
            'Doctor profile not found.'
        )

        return redirect(
            'doctor_dashboard'
        )

    medical_records = MedicalRecord.objects.filter(
        doctor=doctor
    ).select_related(
        'patient__user',
        'appointment'
    ).order_by(
        '-record_date',
        '-id'
    )

    return render(
        request,
        'accounts/doctor_medical_records.html',
        {
            'doctor': doctor,
            'medical_records': medical_records,
        }
    )


# ============================================================
# DOCTOR → SPECIFIC PATIENT MEDICAL RECORDS
# ============================================================

@login_required
def doctor_patient_medical_records(
    request,
    patient_id
):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        messages.error(
            request,
            'Doctor profile not found.'
        )

        return redirect(
            'doctor_dashboard'
        )

    patient = get_object_or_404(
        Patient.objects.select_related('user'),
        id=patient_id
    )

    has_appointment = Appointment.objects.filter(
        doctor=doctor,
        patient=patient
    ).exists()

    if not has_appointment:

        messages.error(
            request,
            'You are not authorized to access this patient.'
        )

        return redirect(
            'doctor_patients'
        )

    medical_records = MedicalRecord.objects.filter(
        patient=patient,
        doctor=doctor
    ).select_related(
        'doctor__user',
        'appointment'
    ).order_by(
        '-record_date',
        '-id'
    )

    return render(
        request,
        'accounts/doctor_patient_medical_records.html',
        {
            'doctor': doctor,
            'patient': patient,
            'medical_records': medical_records,
            'total_records': medical_records.count(),
        }
    )


# ============================================================
# DOCTOR → ADD MEDICAL RECORD FOR SPECIFIC PATIENT
# ============================================================

@login_required
def doctor_add_patient_medical_record(
    request,
    patient_id
):

    if not request.user.is_superuser:

        profile = get_user_profile(request)

        if profile is None:

            messages.error(
                request,
                'Profile not found.'
            )

            return redirect('dashboard')

        if profile.role != 'doctor':

            messages.error(
                request,
                'You are not authorized to access this page.'
            )

            return redirect('dashboard')

        if not profile.is_approved:

            messages.warning(
                request,
                'Your account is waiting for approval.'
            )

            return redirect('login')

    try:

        doctor = request.user.doctor

    except Doctor.DoesNotExist:

        messages.error(
            request,
            'Doctor profile not found.'
        )

        return redirect(
            'doctor_dashboard'
        )

    patient = get_object_or_404(
        Patient.objects.select_related('user'),
        id=patient_id
    )

    has_appointment = Appointment.objects.filter(
        doctor=doctor,
        patient=patient
    ).exists()

    if not has_appointment:

        messages.error(
            request,
            'You are not authorized to access this patient.'
        )

        return redirect(
            'doctor_patients'
        )

    appointments = Appointment.objects.filter(
        doctor=doctor,
        patient=patient
    ).order_by(
        '-appointment_date',
        '-appointment_time'
    )

    if request.method == 'POST':

        diagnosis = request.POST.get(
            'diagnosis',
            ''
        ).strip()

        symptoms = request.POST.get(
            'symptoms',
            ''
        ).strip()

        prescription = request.POST.get(
            'prescription',
            ''
        ).strip()

        treatment = request.POST.get(
            'treatment',
            ''
        ).strip()

        notes = request.POST.get(
            'notes',
            ''
        ).strip()

        appointment_id = request.POST.get(
            'appointment'
        )

        if not diagnosis:

            messages.error(
                request,
                'Diagnosis is required.'
            )

            return render(
                request,
                'accounts/doctor_add_patient_medical_record.html',
                {
                    'doctor': doctor,
                    'patient': patient,
                    'appointments': appointments,
                }
            )

        appointment = None

        if appointment_id:

            try:

                appointment = Appointment.objects.get(
                    id=appointment_id,
                    doctor=doctor,
                    patient=patient
                )

            except Appointment.DoesNotExist:

                messages.error(
                    request,
                    'Invalid appointment selected.'
                )

                return render(
                    request,
                    'accounts/doctor_add_patient_medical_record.html',
                    {
                        'doctor': doctor,
                        'patient': patient,
                        'appointments': appointments,
                    }
                )

        MedicalRecord.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            diagnosis=diagnosis,
            symptoms=symptoms,
            prescription=prescription,
            treatment=treatment,
            notes=notes
        )

        messages.success(
            request,
            'Medical record created successfully.'
        )

        return redirect(
            'doctor_patient_medical_records',
            patient_id=patient.id
        )

    return render(
        request,
        'accounts/doctor_add_patient_medical_record.html',
        {
            'doctor': doctor,
            'patient': patient,
            'appointments': appointments,
        }
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        role = request.POST.get(
            'role',
            'patient'
        ).strip().lower()

        specialization = request.POST.get(
            'specialization',
            ''
        ).strip()

        qualification = request.POST.get(
            'qualification',
            ''
        ).strip()

        experience = request.POST.get(
            'experience',
            '0'
        ).strip()

        consultation_fee = request.POST.get(
            'consultation_fee',
            '0'
        ).strip()

        available_days = request.POST.get(
            'available_days',
            ''
        ).strip()

        is_available = request.POST.get(
            'is_available'
        ) == 'on'

        allowed_roles = [
            'patient',
            'doctor',
            'receptionist'
        ]

        if role not in allowed_roles:
            messages.error(
                request,
                'Please select a valid account type.'
            )
            return redirect('register')

        if not username or not password:
            messages.error(
                request,
                'Username and password are required.'
            )
            return redirect('register')

        if password != confirm_password:
            messages.error(
                request,
                'Passwords do not match.'
            )
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                'Username already exists.'
            )
            return redirect('register')

        if role == 'doctor':

            if not specialization:
                messages.error(
                    request,
                    'Specialization is required for doctor registration.'
                )
                return redirect('register')

            if not qualification:
                messages.error(
                    request,
                    'Qualification is required for doctor registration.'
                )
                return redirect('register')

            try:
                experience_value = int(experience or 0)
                if experience_value < 0:
                    raise ValueError
            except ValueError:
                messages.error(
                    request,
                    'Experience must be a valid positive number.'
                )
                return redirect('register')

            try:
                fee_value = Decimal(consultation_fee or '0')
                if fee_value < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                messages.error(
                    request,
                    'Consultation fee must be a valid amount.'
                )
                return redirect('register')

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone,
            is_approved=False
        )

        if role == 'patient':

            Patient.objects.create(
                user=user,
                phone=phone
            )

        elif role == 'doctor':

            Doctor.objects.create(
                user=user,
                specialization=specialization,
                qualification=qualification,
                phone=phone,
                experience=experience_value,
                consultation_fee=fee_value,
                available_days=available_days,
                is_available=is_available
            )

        messages.success(
            request,
            'Registration successful. Your account is waiting for clinic approval.'
        )

        return redirect(
            'login'
        )

    return render(
        request,
        'accounts/register.html'
    )

