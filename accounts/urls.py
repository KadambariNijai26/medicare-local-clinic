from django.urls import path

from .views import (
    login_view,
    register_view,
    logout_view,

    dashboard,
    admin_dashboard,
    doctor_dashboard,
    receptionist_dashboard,
    patient_dashboard,

    patient_appointments,
    patient_medical_records,

    doctor_appointments,
    doctor_patients,
    doctor_medical_records,
    doctor_patient_medical_records,
    doctor_add_patient_medical_record,

    patient_list,
    add_patient,
    edit_patient,
    delete_patient,

    pending_approvals,
    approve_account,

    doctor_list,
    add_doctor,
    edit_doctor,
    delete_doctor,

    # Receptionist Management
    receptionist_list,
    add_receptionist,

    appointment_list,
    add_appointment,
    edit_appointment,
    delete_appointment,

    medical_record_list,
    add_medical_record,
    edit_medical_record,
    delete_medical_record,
)


urlpatterns = [

    # ============================================================
    # AUTHENTICATION
    # ============================================================

    path(
        'login/',
        login_view,
        name='login'
    ),

    path(
        'register/',
        register_view,
        name='register'
    ),

    path(
        'logout/',
        logout_view,
        name='logout'
    ),


    # ============================================================
    # DASHBOARDS
    # ============================================================

    path(
        'dashboard/',
        dashboard,
        name='dashboard'
    ),

    path(
        'admin-dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'doctor-dashboard/',
        doctor_dashboard,
        name='doctor_dashboard'
    ),

    path(
        'receptionist-dashboard/',
        receptionist_dashboard,
        name='receptionist_dashboard'
    ),

    path(
        'patient-dashboard/',
        patient_dashboard,
        name='patient_dashboard'
    ),


    # ============================================================
    # ACCOUNT APPROVAL
    # ============================================================

    path(
        'pending-approvals/',
        pending_approvals,
        name='pending_approvals'
    ),

    path(
        'pending-approvals/<int:user_id>/approve/',
        approve_account,
        name='approve_account'
    ),


    # ============================================================
    # PATIENT MANAGEMENT
    # ============================================================

    path(
        'patients/',
        patient_list,
        name='patient_list'
    ),

    path(
        'patients/add/',
        add_patient,
        name='add_patient'
    ),

    path(
        'patients/<int:patient_id>/edit/',
        edit_patient,
        name='edit_patient'
    ),

    path(
        'patients/<int:patient_id>/delete/',
        delete_patient,
        name='delete_patient'
    ),


    # ============================================================
    # DOCTOR MANAGEMENT
    # ============================================================

    path(
        'doctors/',
        doctor_list,
        name='doctor_list'
    ),

    path(
        'doctors/add/',
        add_doctor,
        name='add_doctor'
    ),

    path(
        'doctors/<int:doctor_id>/edit/',
        edit_doctor,
        name='edit_doctor'
    ),

    path(
        'doctors/<int:doctor_id>/delete/',
        delete_doctor,
        name='delete_doctor'
    ),


    # ============================================================
    # RECEPTIONIST MANAGEMENT
    # ============================================================

    path(
        'receptionists/',
        receptionist_list,
        name='receptionist_list'
    ),

    path(
        'receptionists/add/',
        add_receptionist,
        name='add_receptionist'
    ),


    # ============================================================
    # APPOINTMENT MANAGEMENT
    # ============================================================

    path(
        'appointments/',
        appointment_list,
        name='appointment_list'
    ),

    path(
        'appointments/add/',
        add_appointment,
        name='add_appointment'
    ),

    path(
        'appointments/<int:appointment_id>/edit/',
        edit_appointment,
        name='edit_appointment'
    ),

    path(
        'appointments/<int:appointment_id>/delete/',
        delete_appointment,
        name='delete_appointment'
    ),


    # ============================================================
    # DOCTOR-SPECIFIC PAGES
    # ============================================================

    path(
        'doctor/appointments/',
        doctor_appointments,
        name='doctor_appointments'
    ),

    path(
        'doctor/patients/',
        doctor_patients,
        name='doctor_patients'
    ),

    path(
        'doctor/medical-records/',
        doctor_medical_records,
        name='doctor_medical_records'
    ),

    path(
        'doctor/patient/<int:patient_id>/medical-records/',
        doctor_patient_medical_records,
        name='doctor_patient_medical_records'
    ),

    path(
        'doctor/patient/<int:patient_id>/medical-records/add/',
        doctor_add_patient_medical_record,
        name='doctor_add_patient_medical_record'
    ),


    # ============================================================
    # PATIENT-SPECIFIC PAGES
    # ============================================================

    path(
        'patient/appointments/',
        patient_appointments,
        name='patient_appointments'
    ),

    path(
        'patient/medical-records/',
        patient_medical_records,
        name='patient_medical_records'
    ),


    # ============================================================
    # MEDICAL RECORD MANAGEMENT
    # ============================================================

    path(
        'medical-records/',
        medical_record_list,
        name='medical_record_list'
    ),

    path(
        'medical-records/add/',
        add_medical_record,
        name='add_medical_record'
    ),

    path(
        'medical-records/<int:record_id>/edit/',
        edit_medical_record,
        name='edit_medical_record'
    ),

    path(
        'medical-records/<int:record_id>/delete/',
        delete_medical_record,
        name='delete_medical_record'
    ),

]