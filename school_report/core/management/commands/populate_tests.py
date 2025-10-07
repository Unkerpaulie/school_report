import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from schools.models import School, Standard, Student
from academics.models import SchoolYear, Term, StandardSubject, StandardTeacher
from reports.models import Test, TestSubject, TestScore, StudentTermReview
from core.utils import get_current_year_and_term, get_current_standard_teacher


class Command(BaseCommand):
    help = 'Populate a school with tests and test scores for the current term'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker()

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=int,
            help='ID of the school to populate (if not provided, will show interactive list)'
        )
        parser.add_argument(
            '--term-id',
            type=int,
            help='ID of the term to populate (if not provided, will use current term)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it'
        )

    def handle(self, *args, **options):
        try:
            # Get school
            if options['school_id']:
                try:
                    school = School.objects.get(id=options['school_id'])
                except School.DoesNotExist:
                    raise CommandError(f'School with ID {options["school_id"]} does not exist.')
            else:
                school = self.select_school_interactive()

            # Get term
            if options['term_id']:
                try:
                    term = Term.objects.get(id=options['term_id'])
                    if term.year.school != school:
                        raise CommandError(f'Term {term} does not belong to school {school}.')
                except Term.DoesNotExist:
                    raise CommandError(f'Term with ID {options["term_id"]} does not exist.')
            else:
                current_year, current_term_number, vacation_status = get_current_year_and_term(school)
                if not current_year:
                    raise CommandError(f'No current year found for school {school}.')
                if not current_term_number:
                    raise CommandError(f'No current term found for school {school}. Currently in vacation period: {vacation_status}')

                # Get the actual Term object
                term = Term.objects.get(year=current_year, term_number=current_term_number)

            self.stdout.write(f'\nSelected School: {school}')
            self.stdout.write(f'Selected Term: {term}')
            self.stdout.write(f'Term Period: {term.start_date} to {term.end_date}')

            if options['dry_run']:
                self.stdout.write(self.style.WARNING('\n--- DRY RUN MODE ---'))

            # Get all standards for this school
            standards = Standard.objects.filter(school=school)
            if not standards.exists():
                raise CommandError(f'No standards found for school {school}.')

            # Process each standard
            with transaction.atomic():
                for standard in standards:
                    self.populate_standard_tests(school, standard, term, options['dry_run'])

                # After creating all tests, populate term reviews
                self.stdout.write('\n--- Populating Term Reviews ---')
                for standard in standards:
                    self.populate_term_reviews(standard, term, options['dry_run'])

            if not options['dry_run']:
                self.stdout.write(
                    self.style.SUCCESS(f'\nSuccessfully populated tests, scores, and term reviews for {school} - {term}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\nDry run completed. No data was actually created.')
                )

        except Exception as e:
            raise CommandError(f'Error: {str(e)}')

    def select_school_interactive(self):
        """Display numbered list of schools and let user select one"""
        schools = School.objects.filter(is_active=True).order_by('name')
        
        if not schools.exists():
            raise CommandError('No active schools found.')

        self.stdout.write('\nAvailable Schools:')
        self.stdout.write('-' * 50)
        
        for i, school in enumerate(schools, 1):
            self.stdout.write(f'{i}. {school.name}')

        while True:
            try:
                choice = input(f'\nEnter school number (1-{schools.count()}): ').strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= schools.count():
                    return schools[choice_num - 1]
                else:
                    self.stdout.write(self.style.ERROR(f'Please enter a number between 1 and {schools.count()}'))
                    
            except (ValueError, KeyboardInterrupt):
                self.stdout.write(self.style.ERROR('\nOperation cancelled.'))
                raise CommandError('User cancelled operation.')

    def populate_standard_tests(self, school, standard, term, dry_run=False):
        """Create tests for a specific standard"""
        self.stdout.write(f'\n--- Processing {standard} ---')

        # Get the teacher assigned to this standard
        teacher_assignment = get_current_standard_teacher(standard, term.year)
        if not teacher_assignment or not teacher_assignment.teacher:
            self.stdout.write(self.style.WARNING(f'No teacher assigned to {standard}. Skipping.'))
            return

        teacher = teacher_assignment.teacher
        self.stdout.write(f'Teacher: {teacher.get_full_name()}')

        # Get subjects for this standard
        subjects = StandardSubject.objects.filter(
            standard=standard,
            year=term.year
        )

        if not subjects.exists():
            self.stdout.write(self.style.WARNING(f'No subjects found for {standard}. Skipping.'))
            return

        # Get enrolled students
        students = Student.objects.filter(
            standard_enrollments__standard=standard,
            standard_enrollments__year=term.year
        ).distinct()

        if not students.exists():
            self.stdout.write(self.style.WARNING(f'No students found for {standard}. Skipping.'))
            return

        self.stdout.write(f'Found {subjects.count()} subjects and {students.count()} students')

        # Calculate test dates based on term duration
        term_duration = (term.end_date - term.start_date).days
        
        test_schedule = [
            ('quiz', term.start_date + timedelta(weeks=2), 50, 1),  # 1 random subject
            ('assignment', term.start_date + timedelta(weeks=4), 100, 1),  # 1 random subject  
            ('midterm', term.start_date + timedelta(weeks=6), 100, 'all'),  # all subjects
            ('quiz', term.start_date + timedelta(weeks=8), 50, 1),  # 1 random subject
            ('final_exam', term.end_date - timedelta(weeks=2), 100, 'all'),  # all subjects
        ]

        # Create tests
        for test_type, test_date, max_score, subject_count in test_schedule:
            # Skip if test date is outside term period
            if test_date < term.start_date or test_date > term.end_date:
                self.stdout.write(
                    self.style.WARNING(f'Skipping {test_type} - date {test_date} is outside term period')
                )
                continue

            self.create_test_with_scores(
                standard, term, test_type, test_date, max_score,
                subjects, students, subject_count, teacher, dry_run
            )

    def create_test_with_scores(self, standard, term, test_type, test_date, max_score,
                               subjects, students, subject_count, teacher, dry_run=False):
        """Create a test with subjects and random scores"""
        
        # Select subjects for this test
        if subject_count == 'all':
            selected_subjects = list(subjects)
            subject_desc = f"all {subjects.count()} subjects"
        else:
            selected_subjects = random.sample(list(subjects), min(subject_count, subjects.count()))
            subject_desc = f"{len(selected_subjects)} random subject(s)"

        test_description = f"{test_type.replace('_', ' ').title()} - {subject_desc}"
        
        self.stdout.write(f'  Creating {test_type} on {test_date} ({subject_desc})')

        if dry_run:
            self.stdout.write(f'    Would create test: {test_description}')
            for subject in selected_subjects:
                self.stdout.write(f'      Subject: {subject.subject_name} (max: {max_score})')
            self.stdout.write(f'      Would generate scores for {students.count()} students')
            return

        # Create the test
        test = Test.objects.create(
            standard=standard,
            term=term,
            test_type=test_type,
            test_date=test_date,
            description=test_description,
            created_by=teacher,  # Set the teacher as creator
            is_finalized=False,  # Start as not finalized
            finalized_at=None
        )

        # Create test subjects and scores
        for subject in selected_subjects:
            # Get or create test subject (should be auto-created by Test.save())
            test_subject = TestSubject.objects.get(
                test=test,
                standard_subject=subject
            )
            
            # Enable this subject and set max score
            test_subject.enabled = True
            test_subject.max_score = max_score
            test_subject.save()

            # Generate random scores for all students
            for student in students:
                # Generate realistic score (70-95% for most students, some lower)
                if random.random() < 0.8:  # 80% of students get good scores
                    score_percentage = random.uniform(0.70, 0.95)
                else:  # 20% get lower scores
                    score_percentage = random.uniform(0.40, 0.75)
                
                score_value = int(score_percentage * max_score)
                
                # Get or create the test score (should be auto-created by Test.save())
                test_score = TestScore.objects.get(
                    test_subject=test_subject,
                    student=student
                )
                test_score.score = score_value
                test_score.save()

        # Finalize the test to trigger report generation
        test.is_finalized = True
        test.finalized_at = timezone.now()
        test.save()

        self.stdout.write(f'    ✓ Created and finalized {test_type} with {len(selected_subjects)} subjects')

    def populate_term_reviews(self, standard, term, dry_run=False):
        """Populate term reviews for all students in a standard"""
        self.stdout.write(f'  Populating term reviews for {standard}')

        # Get enrolled students
        students = Student.objects.filter(
            standard_enrollments__standard=standard,
            standard_enrollments__year=term.year
        ).distinct()

        if not students.exists():
            self.stdout.write(f'    No students found for {standard}')
            return

        if dry_run:
            self.stdout.write(f'    Would populate term reviews for {students.count()} students')
            return

        # Calculate term duration for attendance
        term_duration = (term.end_date - term.start_date).days
        # Estimate school days (roughly 5 days per week, minus holidays)
        estimated_school_days = int(term_duration * 5 / 7 * 0.85)  # 85% to account for holidays

        for student in students:
            # Create or get term review
            term_review, created = StudentTermReview.objects.get_or_create(
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

            # Generate realistic attendance data
            # Most students attend 85-95% of school days
            attendance_rate = random.uniform(0.85, 0.95)
            days_present = int(estimated_school_days * attendance_rate)

            # Late days are typically 5-15% of present days
            late_rate = random.uniform(0.05, 0.15)
            days_late = int(days_present * late_rate)

            # Generate qualitative ratings (1-5 scale, weighted toward positive)
            def generate_rating():
                # 60% chance of 4-5, 30% chance of 3, 10% chance of 1-2
                rand = random.random()
                if rand < 0.6:
                    return random.randint(4, 5)
                elif rand < 0.9:
                    return 3
                else:
                    return random.randint(1, 2)

            # Generate teacher remarks (2 sentences)
            positive_comments = [
                f"{student.first_name} demonstrates excellent understanding of the material.",
                f"{student.first_name} actively participates in class discussions.",
                f"{student.first_name} shows great improvement in their work.",
                f"{student.first_name} is helpful to classmates and respectful to teachers.",
                f"{student.first_name} completes assignments on time and with care.",
                f"{student.first_name} shows creativity in their approach to problems.",
                f"{student.first_name} asks thoughtful questions during lessons.",
                f"{student.first_name} works well independently and in groups."
            ]

            areas_for_improvement = [
                f"{student.first_name} could benefit from more consistent homework completion.",
                f"{student.first_name} should work on speaking up more in class.",
                f"{student.first_name} needs to focus on improving handwriting skills.",
                f"{student.first_name} should continue practicing basic math facts.",
                f"{student.first_name} would benefit from reading more at home.",
                f"{student.first_name} should work on time management skills.",
                f"{student.first_name} needs to be more careful with attention to detail.",
                f"{student.first_name} should continue building confidence in presentations."
            ]

            # Generate 2 sentences - mix of positive and constructive
            if random.random() < 0.7:  # 70% chance of positive first
                sentence1 = random.choice(positive_comments)
                sentence2 = random.choice(areas_for_improvement)
            else:  # 30% chance of improvement first
                sentence1 = random.choice(areas_for_improvement)
                sentence2 = random.choice(positive_comments)

            remarks = f"{sentence1} {sentence2}"

            # Update the term review
            term_review.days_present = days_present
            term_review.days_late = days_late
            term_review.attitude = generate_rating()
            term_review.respect = generate_rating()
            term_review.parental_support = generate_rating()
            term_review.attendance = generate_rating()
            term_review.assignment_completion = generate_rating()
            term_review.class_participation = generate_rating()
            term_review.time_management = generate_rating()
            term_review.remarks = remarks
            term_review.save()

        self.stdout.write(f'    ✓ Populated term reviews for {students.count()} students')
