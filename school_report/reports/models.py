from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.apps import apps
from schools.models import Student


class Test(models.Model):
    """
    Represents a test created by a teacher for a standard
    """
    TEST_TYPE_CHOICES = [
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('midterm', 'Mid-Term Test'),
        ('endterm', 'End of Term Test'),  # This is the formal term assessment
        ('project', 'Project'),
        ('other', 'Other'),
    ]

    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='tests')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='tests', null=True)  # Direct relationship to Term
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    test_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, 
                                  related_name='created_tests',
                                  limit_choices_to={'user_type': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-test_date']

    def __str__(self):
        return f"{self.term} - {self.test_type} - {self.standard}"
    
    def clean(self):
        """
        Validate that test date falls within the term dates and link to the appropriate Term
        """
        from django.core.exceptions import ValidationError
        
        if not (self.term.start_date <= self.test_date <= self.term.end_date):
            raise ValidationError({
                'test_date': f'Test date must be within {self.term} '
                            f'({self.term.start_date} to {self.term.end_date})'
            })
    
    def save(self, *args, **kwargs):
        """
        Save the Test and ensure it's linked to the appropriate Term
        Auto-create test subjects and scores for new tests
        """
        self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Auto-create test subjects and scores for new tests
        if is_new:
            self.create_test_subjects_and_scores()

    def create_test_subjects_and_scores(self):
        """
        Auto-create TestSubject entries for all available subjects in the standard/year
        and TestScore entries for all enrolled students (all disabled and zero by default)
        """
        from academics.models import StandardSubject
        from schools.models import Student
        from core.utils import get_current_student_enrollment

        # Get all subjects for this standard and year
        standard_subjects = StandardSubject.objects.filter(
            standard=self.standard,
            year=self.term.year
        )

        # Get all currently enrolled students for this standard and year
        potential_students = Student.objects.filter(
            standard_enrollments__standard=self.standard,
            standard_enrollments__year=self.term.year
        ).distinct()

        # Filter to only currently enrolled students
        enrolled_students = []
        for student in potential_students:
            current_enrollment = get_current_student_enrollment(student, self.term.year)
            if current_enrollment and current_enrollment.standard == self.standard:
                enrolled_students.append(student)

        # Create TestSubject entries for all subjects (disabled by default)
        test_subjects = []
        for standard_subject in standard_subjects:
            test_subject, created = TestSubject.objects.get_or_create(
                test=self,
                standard_subject=standard_subject,
                defaults={
                    'max_score': 100,
                    'enabled': False
                }
            )
            test_subjects.append(test_subject)

        # Create TestScore entries for all students and all subjects (score=0 by default)
        for test_subject in test_subjects:
            for student in enrolled_students:
                TestScore.objects.get_or_create(
                    test_subject=test_subject,
                    student=student,
                    defaults={'score': 0}
                )

    @property
    def enabled_subjects_count(self):
        """Return the count of enabled subjects for this test"""
        return self.subjects.filter(enabled=True).count()

    @classmethod
    def get_term_tests(cls, term, standard=None):
        """
        Get all end-of-term tests for a specific year and term
        
        This method provides a way to access the formal term assessments
        (equivalent to what was previously in the TermTest model)
        """
        filters = {
            'term': term,
            'test_type': 'endterm',
        }
        
        if standard:
            filters['standard'] = standard
            
        return cls.objects.filter(**filters)

class TestSubject(models.Model):
    """
    Represents a subject included in a test
    """
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='subjects')
    standard_subject = models.ForeignKey('academics.StandardSubject', on_delete=models.CASCADE, related_name='test_subjects')
    max_score = models.PositiveIntegerField(default=100)
    enabled = models.BooleanField(default=False, help_text="Whether this subject is active for this test")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['test', 'standard_subject']

    def __str__(self):
        return f"{self.test} - {self.standard_subject.subject_name}"

class TestScore(models.Model):
    """
    Represents a student's score in a subject for a specific test
    """
    test_subject = models.ForeignKey(TestSubject, on_delete=models.CASCADE, related_name='student_scores')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='test_scores')
    score = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['test_subject', 'student']
        verbose_name = "Test Score"
        verbose_name_plural = "Test Scores"

    def __str__(self):
        return f"{self.test_subject} - {self.student} - {self.score}/{self.test_subject.max_score}"

    @property
    def percentage(self):
        """Calculate percentage score"""
        return (self.score / self.test_subject.max_score) * 100

    @classmethod
    def get_student_term_average(cls, student, year, term):
        """
        Calculate the average score for a student across all subjects in end-of-term tests
        """
        scores = cls.objects.filter(
            student=student,
            test_subject__test__year=year,
            test_subject__test__term=term,
            test_subject__test__test_type='endterm'
        )

        if not scores.exists():
            return 0

        total_percentage = sum(score.percentage for score in scores)
        return total_percentage / scores.count()

class StudentTermReview(models.Model):
    """
    Represents a student's term review for a term
    """
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Below Average'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]

    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='student_reviews', null=True)  # Direct relationship to Term
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='term_reviews')
    # Attendance
    days_present = models.PositiveIntegerField()
    days_late = models.PositiveIntegerField(default=0)
    # Qualitative attributes
    attitude = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    respect = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    parental_support = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    attendance = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    assignment_completion = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    class_participation = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    time_management = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    remarks = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['term', 'student']

    def __str__(self):
        return f"{self.term} - {self.student} - {self.days_present} days present"

    def get_term_days(self):
        """Get the total number of school days in the term"""
        if self.term:
            return self.term.school_days
        return 0

    @property
    def attendance_percentage(self):
        """Calculate attendance percentage"""
        term_days = self.get_term_days()
        if term_days > 0:
            return (self.days_present / term_days) * 100
        return 0
    

