from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from academics.models import Year, StandardSubject, Standard
from schools.models import Student, Teacher

# Common choices
TERM_CHOICES = [
    (1, 'Term 1'),
    (2, 'Term 2'),
    (3, 'Term 3'),
]

TEST_TYPE_CHOICES = [
    ('assignment', 'Assignment'),
    ('quiz', 'Quiz'),
    ('midterm', 'Mid-Term Test'),
    ('endterm', 'End of Term Test'),
    ('project', 'Project'),
    ('other', 'Other'),
]

TEST_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('finalized', 'Finalized'),
]

class TermTest(models.Model):
    """
    Represents a term test for a specific subject in a standard
    """

    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='term_tests')
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    standard_subject = models.ForeignKey(StandardSubject, on_delete=models.CASCADE, related_name='term_tests')
    max_marks = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term', 'standard_subject']

    def __str__(self):
        return f"{self.year} - {self.get_term_display()} - {self.standard_subject.subject.name}"

class StudentSubjectScore(models.Model):
    """
    Represents a student's score in a subject for a specific term
    """
    term_test = models.ForeignKey(TermTest, on_delete=models.CASCADE, related_name='student_scores')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_scores')
    score = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['term_test', 'student']
        verbose_name = "Student Subject Score"
        verbose_name_plural = "Student Subject Scores"

    def __str__(self):
        return f"{self.term_test} - {self.student} - {self.score}/{self.term_test.max_marks}"

    @property
    def percentage(self):
        """Calculate percentage score"""
        return (self.score / self.term_test.max_marks) * 100

    @classmethod
    def get_student_term_average(cls, student, year, term):
        """
        Calculate the average score for a student across all subjects in a term
        """
        scores = cls.objects.filter(
            student=student,
            term_test__year=year,
            term_test__term=term
        )

        if not scores.exists():
            return 0

        total_percentage = sum(score.percentage for score in scores)
        return total_percentage / scores.count()

class StudentAttendance(models.Model):
    """
    Represents a student's attendance record for a term
    """

    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='student_attendances')
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    days_present = models.PositiveIntegerField()
    days_late = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term', 'student']

    def __str__(self):
        return f"{self.year} - {self.get_term_display()} - {self.student}"

    def get_term_days(self):
        """Get the total number of school days in the term"""
        if self.term == 1:
            return self.year.term1_school_days
        elif self.term == 2:
            return self.year.term2_school_days
        else:
            return self.year.term3_school_days

    @property
    def attendance_percentage(self):
        """Calculate attendance percentage"""
        term_days = self.get_term_days()
        if term_days > 0:
            return (self.days_present / term_days) * 100
        return 0

class QualitativeRating(models.Model):
    """
    Represents qualitative ratings for a student in a term
    """

    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Below Average'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]

    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='student_ratings')
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='qualitative_ratings')

    # Qualitative attributes
    attitude = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    respect = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    parental_support = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    attendance = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    assignment_completion = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    class_participation = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    time_management = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term', 'student']

    def __str__(self):
        return f"{self.year} - {self.get_term_display()} - {self.student}"

class TeacherRemark(models.Model):
    """
    Represents a teacher's remarks for a student in a term
    """

    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='teacher_remarks')
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='teacher_remarks')
    remarks = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term', 'student']

    def __str__(self):
        return f"{self.year} - {self.get_term_display()} - {self.student}"


class Test(models.Model):
    """
    Represents a test created by a teacher for a standard
    """
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='tests')
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='tests_this_year')
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    test_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-test_date']

    def __str__(self):
        return f"{self.get_test_type_display()} - {self.standard} - {self.test_date}"

    def is_editable(self):
        """Always return True since we're not using status anymore"""
        return True


class TestSubject(models.Model):
    """
    Represents a subject included in a test with its maximum score
    """
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='subjects')
    standard_subject = models.ForeignKey(StandardSubject, on_delete=models.CASCADE, related_name='test_inclusions')
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['test', 'standard_subject']

    def __str__(self):
        return f"{self.standard_subject.subject.name} - Max: {self.max_score}"


class TestScore(models.Model):
    """
    Represents a student's score for a subject in a test
    """
    test_subject = models.ForeignKey(TestSubject, on_delete=models.CASCADE, related_name='student_scores')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='test_scores')
    score = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['test_subject', 'student']

    def __str__(self):
        return f"{self.student} - {self.test_subject.standard_subject.subject.name} - {self.score}/{self.test_subject.max_score}"

    @property
    def percentage(self):
        """Calculate percentage score"""
        if self.test_subject.max_score > 0:
            return (self.score / self.test_subject.max_score) * 100
        return 0

    def clean(self):
        """Validate that score is not greater than max_score"""
        from django.core.exceptions import ValidationError

        if self.score > self.test_subject.max_score:
            raise ValidationError({'score': f'Score cannot be greater than the maximum score of {self.test_subject.max_score}.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
