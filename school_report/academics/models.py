from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import UserProfile

class SchoolYear(models.Model):
    """
    Represents an academic year with three terms
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='years')
    start_year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'start_year']
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.start_year}-{self.start_year + 1}"

class Term(models.Model):
    """
    Represents a term within an academic year
    """
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='terms')
    term_number = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    school_days = models.PositiveIntegerField()

    # Term finalization tracking
    is_finalized = models.BooleanField(default=False, help_text="Whether this term has been finalized (no more tests can be created)")
    finalized_at = models.DateTimeField(null=True, blank=True, help_text="When this term was finalized")
    finalized_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='finalized_terms', help_text="Who finalized this term")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term_number']
        ordering = ['year', 'term_number']

    def __str__(self):
        return f"{self.year} - {self.get_term_number_display()}"

    def can_be_finalized(self):
        """
        Check if this term can be finalized
        A term can be finalized if all reports for all classes in this term are finalized
        """
        if self.is_finalized:
            return False, "Term is already finalized"

        # Import here to avoid circular imports
        from reports.models import StudentTermReview

        # Get all reports for this term
        term_reports = StudentTermReview.objects.filter(term=self)

        if not term_reports.exists():
            return False, "No reports found for this term"

        # Check if all reports are finalized
        unfinalized_reports = term_reports.filter(is_finalized=False)
        if unfinalized_reports.exists():
            return False, f"{unfinalized_reports.count()} reports are not yet finalized"

        return True, "Term can be finalized"

    def finalize_term(self, user):
        """
        Finalize this term, preventing new test creation
        """
        from django.utils import timezone

        can_finalize, message = self.can_be_finalized()
        if not can_finalize:
            return False, message

        self.is_finalized = True
        self.finalized_at = timezone.now()
        self.finalized_by = user
        self.save()

        return True, "Term finalized successfully. No new tests can be created for this term."
    
class StandardTeacher(models.Model):
    """
    Represents teacher assignment history for a specific academic year.
    Latest record with non-null standard = current assignment.
    Latest record with null standard = unassigned.
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_teachers')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE,
                               related_name='teacher_assignments',
                               null=True, blank=True)  # Null = unassigned
    teacher = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE,
                               related_name='standard_assignments',
                               limit_choices_to={'user_type': 'teacher'},
                               null=True, blank=True)  # Null = unassigned
    assigned_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='teacher_assignments_made', help_text="User who made this assignment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove unique constraint to allow assignment history
        ordering = ['-created_at']  # Latest first

    def __str__(self):
        if self.standard and self.teacher:
            return f"{self.year} - {self.standard} - {self.teacher.get_full_name()}"
        elif self.standard and not self.teacher:
            return f"{self.year} - {self.standard} - No Teacher Assigned"
        elif not self.standard and self.teacher:
            return f"{self.year} - {self.teacher.get_full_name()} - Unassigned"
        else:
            return f"{self.year} - Invalid Assignment Record"

class SchoolEnrollment(models.Model):
    """
    Represents the registration relationship between a student and a school.
    This is persistent across academic years - students don't need to be "re-enrolled"
    in the school each year, only reassigned to different classes.
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='enrolled_students')
    student = models.ForeignKey('schools.Student', on_delete=models.CASCADE, related_name='school_registrations')
    enrollment_date = models.DateField(null=True, blank=True, help_text="Date when student was enrolled in the school")
    graduation_date = models.DateField(null=True, blank=True, help_text="Date when student graduated or left")
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about student transfers or status changes")
    is_active = models.BooleanField(default=True, help_text="False if student has graduated or left the school")
    enrolled_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='school_enrollments_made', help_text="User who enrolled this student")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'student']  # One registration record per student per school
        ordering = ['student__last_name', 'student__first_name']
        verbose_name = 'School Enrollment'
        verbose_name_plural = 'School Enrollments'

    def __str__(self):
        status_str = " (Graduated)" if not self.is_active else ""
        return f"{self.student} - {self.school.name}{status_str}"


class StandardEnrollment(models.Model):
    """
    Represents student class assignment history for a specific academic year.
    Latest record with non-null standard = current class assignment.
    Latest record with null standard = unassigned (between classes).
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='year_standard_enrollments')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE,
                               related_name='student_assignments',
                               null=True, blank=True)  # Null = unassigned
    student = models.ForeignKey('schools.Student', on_delete=models.CASCADE, related_name='standard_enrollments') # renamed from class_assignments
    enrolled_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='class_enrollments_made', help_text="User who enrolled this student in the class")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove unique constraint to allow assignment history
        ordering = ['-created_at']  # Latest first
        verbose_name = 'Standard Enrollment'
        verbose_name_plural = 'Standard Enrollments'

    def __str__(self):
        if self.standard:
            return f"{self.year} - {self.standard} - {self.student}"
        else:
            return f"{self.year} - Unassigned - {self.student}"


# Keep the old Enrollment model name as an alias for backward compatibility
# Enrollment = StandardEnrollment

class StandardSubject(models.Model):
    """
    Represents a subject taught in a standard for a specific academic year
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_subjects')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='assigned_subjects')
    subject_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, 
                                 related_name='created_subjects',
                                 limit_choices_to={'user_type': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'subject_name']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.subject_name}"

class SchoolStaff(models.Model):
    """
    Represents the employment relationship between a staff member and a school.
    This is persistent across academic years - staff don't need to be "reassigned"
    to the school each year, only teachers get reassigned to different classes.
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='staff_members')
    staff = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='school_employment')
    position = models.CharField(max_length=100, blank=True, null=True,
                               help_text="Position or role in the school (e.g., Principal, Vice Principal, Secretary)")
    hire_date = models.DateField(null=True, blank=True, help_text="Date when staff member was hired")
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about staff transfers or role changes")
    is_active = models.BooleanField(default=True, help_text="False if staff member has left the school")
    added_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='staff_additions_made', help_text="User who added this staff member")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'staff']  # One employment record per staff per school
        ordering = ['staff__user__last_name', 'staff__user__first_name']
        verbose_name = 'School Staff Member'
        verbose_name_plural = 'School Staff Members'

    def __str__(self):
        position_str = f" ({self.position})" if self.position else ""
        return f"{self.staff.get_full_name()}{position_str} - {self.school.name}"


class AcademicTransition(models.Model):
    """
    Track academic year transition progress for a school.
    Ensures sequential processing and prevents out-of-order operations.
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='academic_transitions')
    from_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='transitions_from')
    to_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='transitions_to')

    # Step 1: Prerequisites
    next_year_verified = models.BooleanField(default=False, help_text="Next academic year setup verified")

    # Step 2: Teacher unassignment
    teachers_unassigned = models.BooleanField(default=False, help_text="All teachers unassigned from classes")
    teachers_unassigned_at = models.DateTimeField(null=True, blank=True)

    # Step 3: Sequential student graduation/advancement (Standard 5 to Infant 1)
    std5_processed = models.BooleanField(default=False, help_text="Standard 5 students graduated")
    std5_processed_at = models.DateTimeField(null=True, blank=True)

    std4_processed = models.BooleanField(default=False, help_text="Standard 4 students advanced")
    std4_processed_at = models.DateTimeField(null=True, blank=True)

    std3_processed = models.BooleanField(default=False, help_text="Standard 3 students advanced")
    std3_processed_at = models.DateTimeField(null=True, blank=True)

    std2_processed = models.BooleanField(default=False, help_text="Standard 2 students advanced")
    std2_processed_at = models.DateTimeField(null=True, blank=True)

    std1_processed = models.BooleanField(default=False, help_text="Standard 1 students advanced")
    std1_processed_at = models.DateTimeField(null=True, blank=True)

    inf2_processed = models.BooleanField(default=False, help_text="Infant 2 students advanced")
    inf2_processed_at = models.DateTimeField(null=True, blank=True)

    inf1_processed = models.BooleanField(default=False, help_text="Infant 1 students advanced")
    inf1_processed_at = models.DateTimeField(null=True, blank=True)

    # Step 4: New student registration
    new_students_registered = models.BooleanField(default=False, help_text="New Infant 1 students registered")
    new_students_registered_at = models.DateTimeField(null=True, blank=True)

    # Step 5: Teacher reassignment (handled by existing system)
    teachers_reassigned = models.BooleanField(default=False, help_text="Teachers assigned to new classes")
    teachers_reassigned_at = models.DateTimeField(null=True, blank=True)

    # Overall status
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['school', 'from_year', 'to_year']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.school.name} Transition: {self.from_year} → {self.to_year}"

    @property
    def is_complete(self):
        """Check if all transition steps are complete"""
        return all([
            self.next_year_verified,
            self.teachers_unassigned,
            self.std5_processed,
            self.std4_processed,
            self.std3_processed,
            self.std2_processed,
            self.std1_processed,
            self.inf2_processed,
            self.inf1_processed,
            self.new_students_registered,
            self.teachers_reassigned,
        ])

    @property
    def progress_percentage(self):
        """Calculate completion percentage"""
        # Core steps: next year verification + 7 student processing steps + new students + teacher reassignment
        total_steps = 10
        completed_steps = sum([
            self.next_year_verified,
            self.std5_processed,
            self.std4_processed,
            self.std3_processed,
            self.std2_processed,
            self.std1_processed,
            self.inf2_processed,
            self.inf1_processed,
            self.new_students_registered,
            self.teachers_reassigned,
        ])
        return int((completed_steps / total_steps) * 100)

    def get_next_available_standard(self):
        """
        Get the next standard that can be processed based on sequential requirements.
        Returns None if no standards are available for processing.
        """
        # Sequential processing: Std 5 → 4 → 3 → 2 → 1 → Inf 2 → Inf 1
        if not self.std5_processed:
            return 'STD5'
        elif not self.std4_processed:
            return 'STD4'
        elif not self.std3_processed:
            return 'STD3'
        elif not self.std2_processed:
            return 'STD2'
        elif not self.std1_processed:
            return 'STD1'
        elif not self.inf2_processed:
            return 'INF2'
        elif not self.inf1_processed:
            return 'INF1'
        else:
            return None  # All standards processed

