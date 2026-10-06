from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('patient', 'Patient'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='receptionist'
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    is_approved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Patient(models.Model):

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient'
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    blood_group = models.CharField(
        max_length=3,
        choices=BLOOD_GROUP_CHOICES,
        blank=True
    )

    emergency_contact = models.CharField(
        max_length=15,
        blank=True
    )

    medical_history = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Doctor(models.Model):

    SPECIALIZATION_CHOICES = (
        ('general', 'General Physician'),
        ('cardiology', 'Cardiologist'),
        ('dermatology', 'Dermatologist'),
        ('orthopedic', 'Orthopedic'),
        ('pediatrician', 'Pediatrician'),
        ('gynecology', 'Gynecologist'),
        ('dentist', 'Dentist'),
        ('neurology', 'Neurologist'),
        ('other', 'Other'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor'
    )

    specialization = models.CharField(
        max_length=50,
        choices=SPECIALIZATION_CHOICES,
        default='general'
    )

    qualification = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    experience = models.PositiveIntegerField(
        default=0,
        help_text='Experience in years'
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    available_days = models.CharField(
        max_length=200,
        blank=True
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Dr. {self.user.get_full_name()}"
            f" - {self.get_specialization_display()}"
        )


class Appointment(models.Model):

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    appointment_date = models.DateField()

    appointment_time = models.TimeField()

    reason = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.patient} - "
            f"Dr. {self.doctor.user.get_full_name()} - "
            f"{self.appointment_date}"
        )


class MedicalRecord(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_records'
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    diagnosis = models.TextField()

    symptoms = models.TextField(
        blank=True
    )

    prescription = models.TextField(
        blank=True
    )

    treatment = models.TextField(
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    record_date = models.DateField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.patient} - "
            f"{self.record_date}"
        )