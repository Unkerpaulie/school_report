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
        ('project', 'Project'),
        ('final_exam', 'Final Exam'),  # Special test type that triggers report generation
        ('other', 'Other'),
    ]

    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='tests')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='tests', null=True)  # Direct relationship to Term
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    test_date = models.DateField()
    description = models.TextField(blank=True, null=True)

    # Finalization tracking
    is_finalized = models.BooleanField(default=False, help_text="Whether this test has been finalized")
    finalized_at = models.DateTimeField(null=True, blank=True, help_text="When this test was finalized")
    finalized_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='finalized_tests', help_text="Who finalized this test")

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

    def finalize_test(self, user):
        """
        Finalize this test and update term reviews accordingly
        """
        from django.utils import timezone

        if self.is_finalized:
            return False, "Test is already finalized"

        # Mark test as finalized
        self.is_finalized = True
        self.finalized_at = timezone.now()
        self.finalized_by = user
        self.save()

        # Update term reviews based on test type
        if self.test_type == 'final_exam':
            # Final exam: Update final exam scores and trigger report generation
            self._update_final_exam_scores()
            return True, "Final exam finalized! Term reports updated."
        else:
            # Regular test: Update term assessment averages
            self._update_term_assessments()
            return True, "Test finalized and term assessments updated."

    def _update_final_exam_scores(self):
        """Update final exam scores in StudentSubjectScore records"""
        # Get all scores for this test
        test_scores = TestScore.objects.filter(
            test_subject__test=self,
            test_subject__enabled=True
        ).select_related('student', 'test_subject__standard_subject')

        for test_score in test_scores:
            # Find or create the student's term review
            term_review, created = StudentTermReview.objects.get_or_create(
                term=self.term,
                student=test_score.student,
                defaults={
                    'days_present': 0,
                    'days_late': 0,
                    'attitude': 3,
                    'respect': 3,
                    'parental_support': 3,
                    'attendance': 3,
                    'assignment_completion': 3,
                    'class_participation': 3,
                    'time_management': 3,
                    'remarks': ''
                }
            )

            # Find or create the subject score record
            subject_score, created = StudentSubjectScore.objects.get_or_create(
                term_review=term_review,
                standard_subject=test_score.test_subject.standard_subject,
                defaults={
                    'term_assessment_percentage': 0.0,
                    'final_exam_score': 0,
                    'final_exam_max_score': 100
                }
            )

            # Update final exam score
            subject_score.update_final_exam_score(test_score)

    def _update_term_assessments(self):
        """Update term assessment averages in StudentSubjectScore records"""
        # Get all scores for this test
        test_scores = TestScore.objects.filter(
            test_subject__test=self,
            test_subject__enabled=True
        ).select_related('student', 'test_subject__standard_subject')

        # Group by student and subject
        student_subjects = {}
        for test_score in test_scores:
            key = (test_score.student.id, test_score.test_subject.standard_subject.id)
            if key not in student_subjects:
                student_subjects[key] = {
                    'student': test_score.student,
                    'standard_subject': test_score.test_subject.standard_subject
                }

        # Update term assessments for each student-subject combination
        for (student_id, subject_id), data in student_subjects.items():
            # Find or create the student's term review
            term_review, created = StudentTermReview.objects.get_or_create(
                term=self.term,
                student=data['student'],
                defaults={
                    'days_present': 0,
                    'days_late': 0,
                    'attitude': 3,
                    'respect': 3,
                    'parental_support': 3,
                    'attendance': 3,
                    'assignment_completion': 3,
                    'class_participation': 3,
                    'time_management': 3,
                    'remarks': ''
                }
            )

            # Find or create the subject score record
            subject_score, created = StudentSubjectScore.objects.get_or_create(
                term_review=term_review,
                standard_subject=data['standard_subject'],
                defaults={
                    'term_assessment_percentage': 0.0,
                    'final_exam_score': 0,
                    'final_exam_max_score': 100
                }
            )

            # Update term assessment average
            subject_score.update_term_assessment()

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

    @classmethod
    def generate_blank_reports(cls, term, standard):
        """
        Generate blank term reports for all students in a standard for a given term
        """
        from core.utils import get_current_student_enrollment
        from academics.models import StandardSubject

        # Get all students enrolled in this standard for the term's year
        potential_students = Student.objects.filter(
            standard_enrollments__standard=standard,
            standard_enrollments__year=term.year
        ).distinct()

        # Filter to only currently enrolled students
        enrolled_students = []
        for student in potential_students:
            current_enrollment = get_current_student_enrollment(student, term.year)
            if current_enrollment and current_enrollment.standard == standard:
                enrolled_students.append(student)

        # Create blank reports for each student
        reports_created = 0
        for student in enrolled_students:
            report, created = cls.objects.get_or_create(
                term=term,
                student=student,
                defaults={
                    'days_present': 0,
                    'days_late': 0,
                    'attitude': 3,
                    'respect': 3,
                    'parental_support': 3,
                    'attendance': 3,
                    'assignment_completion': 3,
                    'class_participation': 3,
                    'time_management': 3,
                    'remarks': ''
                }
            )
            if created:
                reports_created += 1

                # Create subject score entries for this report
                standard_subjects = StandardSubject.objects.filter(
                    standard=standard,
                    year=term.year
                )

                for subject in standard_subjects:
                    StudentSubjectScore.objects.get_or_create(
                        term_review=report,
                        standard_subject=subject,
                        defaults={
                            'term_assessment_percentage': 0.0,
                            'final_exam_score': 0,
                            'final_exam_max_score': 100
                        }
                    )

        return reports_created


class StudentSubjectScore(models.Model):
    """
    Represents a student's scores for a specific subject in a term review
    """
    term_review = models.ForeignKey(StudentTermReview, on_delete=models.CASCADE, related_name='subject_scores')
    standard_subject = models.ForeignKey('academics.StandardSubject', on_delete=models.CASCADE, related_name='student_scores')

    # Term Assessment: Average of all non-final tests (quizzes, midterms, assignments, projects)
    term_assessment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                                   help_text="Average percentage of all term assessments")

    # Final Exam: Separate score
    final_exam_score = models.PositiveIntegerField(default=0, help_text="Raw score on final exam")
    final_exam_max_score = models.PositiveIntegerField(default=100, help_text="Maximum possible score on final exam")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['term_review', 'standard_subject']
        verbose_name = "Student Subject Score"
        verbose_name_plural = "Student Subject Scores"

    def __str__(self):
        return f"{self.term_review.student} - {self.standard_subject.subject_name} - {self.term_review.term}"

    @property
    def final_exam_percentage(self):
        """Calculate final exam percentage"""
        if self.final_exam_max_score > 0:
            return (self.final_exam_score / self.final_exam_max_score) * 100
        return 0

    @property
    def final_grade(self):
        """Calculate final grade based on final exam percentage"""
        percentage = self.final_exam_percentage
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 60:
            return 'C'
        elif percentage >= 50:
            return 'D'
        else:
            return 'F'

    def update_term_assessment(self):
        """
        Calculate and update term assessment percentage from all non-final tests
        """
        from django.db.models import Avg

        # Get all non-final test scores for this student and subject
        term_scores = TestScore.objects.filter(
            student=self.term_review.student,
            test_subject__standard_subject=self.standard_subject,
            test_subject__test__term=self.term_review.term,
            test_subject__test__test_type__in=['quiz', 'midterm', 'assignment', 'project'],
            test_subject__test__is_finalized=True
        )

        if term_scores.exists():
            # Calculate average percentage
            total_percentage = sum(score.percentage for score in term_scores)
            self.term_assessment_percentage = total_percentage / term_scores.count()
            self.save()

        return self.term_assessment_percentage

    def update_final_exam_score(self, test_score):
        """
        Update final exam score from a finalized final exam test
        """
        if test_score.test_subject.test.test_type == 'final_exam':
            self.final_exam_score = test_score.score
            self.final_exam_max_score = test_score.test_subject.max_score
            self.save()

            return True
        return False

