import random
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.db import transaction

from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import Year, StandardSubject, Subject
from reports.models import Test, TestSubject, TestScore, TEST_TYPE_CHOICES

class Command(BaseCommand):
    help = 'Generate demo data for the school reporting system'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker()
        self.usernames = set()  # Track used usernames

    def add_arguments(self, parser):
        num_students = random.randint(13, 18)
        parser.add_argument('--schools', type=int, default=1, help='Number of schools to create')
        parser.add_argument('--teachers', type=int, default=7, help='Number of teachers per school')
        parser.add_argument('--admin-staff', type=int, default=2, help='Number of admin staff per school')
        parser.add_argument('--students', type=int, default=num_students, help='Number of students per standard')
        parser.add_argument('--subjects', type=int, default=5, help='Number of subjects per standard')
        parser.add_argument('--tests', type=int, default=3, help='Number of tests per term')

    def generate_phone_number(self):
        return f"(868) {random.choice([2, 3, 4, 6, 7])}{str(random.randint(0, 99)).zfill(2)}-{str(random.randint(0, 9999)).zfill(4)}"

    def generate_unique_username(self, first_name, last_name):
        """Generate a unique username based on first and last name"""
        base_username = f"{first_name[0].lower()}{last_name.lower()}"[:15]
        username = base_username
        counter = 2
        
        while username in self.usernames:
            username = f"{base_username}{counter}"[:15]
            counter += 1
            
        self.usernames.add(username)
        return username

    def create_user(self, first_name, last_name, user_type, school=None, title=None, position=None, phone_number=None):
        """Create a user with the given details"""
        username = self.generate_unique_username(first_name, last_name)
        email = f"{username}@moe.gov.tt"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password="ChangeMe!",
            first_name=first_name,
            last_name=last_name
        )
        
        # Update profile
        profile = user.profile
        profile.user_type = user_type
        profile.phone_number = phone_number or self.generate_phone_number()
        profile.must_change_password = True
        
        # Set school-specific fields
        if school:
            profile.school = school
        
        # Set title if provided
        if title:
            profile.title = title
            
        # Set position for admin staff
        if position and user_type == 'administration':
            profile.position = position
            
        profile.save()
        
        return user

    def handle(self, *args, **options):
        num_schools = options['schools']
        num_teachers = options['teachers']
        num_admin_staff = options['admin_staff']
        num_students = options['students']
        num_subjects = options['subjects']
        num_tests = options['tests']
        
        self.stdout.write(self.style.SUCCESS(f'Starting demo data generation...'))
        
        with transaction.atomic():
            for s in range(num_schools):
                # 1. Create principal
                principal_first_name = self.fake.first_name()
                principal_last_name = self.fake.last_name()
                principal_title = random.choice(['Mr', 'Mrs', 'Ms', 'Dr'])
                principal_user = self.create_user(
                    principal_first_name, 
                    principal_last_name, 
                    'principal',
                    title=principal_title
                )
                
                self.stdout.write(f'Created principal: {principal_user.profile.get_full_name()}')
                
                # 2. Create school and current year
                school_name = f"{self.fake.city()} {random.choice(['Government Primary', 'RC', 'AC', 'SDA', 'Presbyterian', 'Hindu'])} School"
                school = School.objects.create(
                    name=school_name,
                    address=self.fake.address(),
                    contact_phone=self.generate_phone_number(),
                    contact_email=f"info@{school_name.lower().replace(' ', '')}.gov.tt",
                    principal_user=principal_user
                )
                
                # Update principal's profile with school
                principal_user.profile.school = school
                principal_user.profile.save()
                
                self.stdout.write(f'Created school: {school.name}')
                
                # Create current year
                current_year = Year.objects.create(
                    start_year=2024,
                    term1_start_date=date(2024, 9, 2),
                    term1_end_date=date(2024, 12, 20),
                    term1_school_days=80,
                    term2_start_date=date(2025, 1, 6),
                    term2_end_date=date(2025, 4, 10),
                    term2_school_days=70,
                    term3_start_date=date(2025, 4, 28),
                    term3_end_date=date(2025, 6, 27),
                    term3_school_days=45
                )
                
                self.stdout.write(f'Created year: {current_year}')
                
                # 3. Create admin staff
                admin_staff_list = []
                for a in range(num_admin_staff):
                    first_name = self.fake.first_name()
                    last_name = self.fake.last_name()
                    title = random.choice(['Mr', 'Mrs', 'Ms', 'Dr'])
                    position = random.choice(['Vice Principal', 'Secretary', 'Administrator'])
                    
                    admin_user = self.create_user(
                        first_name, 
                        last_name, 
                        'administration',
                        school=school,
                        title=title,
                        position=position
                    )
                    
                    admin_staff_list.append(admin_user.profile)
                    self.stdout.write(f'Created admin staff: {admin_user.profile.get_full_name()} ({position})')
                
                # Create teachers
                teachers = []
                for t in range(num_teachers):
                    first_name = self.fake.first_name()
                    last_name = self.fake.last_name()
                    title = random.choice(UserProfile.TITLE_CHOICES)[0]
                    
                    teacher_user = self.create_user(
                        first_name, 
                        last_name, 
                        'teacher',
                        school=school,
                        title=title
                    )
                    
                    teachers.append(teacher_user.profile)
                    self.stdout.write(f'Created teacher: {teacher_user.profile.get_full_name()}')
                
                # 4. Create students and assign to standards
                standards = Standard.objects.filter(school=school)
                
                for a, standard in enumerate(standards):
                    for _ in range(num_students):
                        first_name = self.fake.first_name()
                        last_name = self.fake.last_name()
                        dob = self.fake.date_of_birth(minimum_age=a+5, maximum_age=a+6)
                        
                        student = Student.objects.create(
                            school=school,
                            standard=standard,
                            first_name=first_name,
                            last_name=last_name,
                            date_of_birth=dob,
                            contact_email=self.fake.email(),
                            contact_phone=self.generate_phone_number(),
                            parent_name=f"{self.fake.first_name()} {last_name}" if random.random() < 0.8 else f"{self.fake.first_name()} {self.fake.last_name()}"
                        )
                        self.stdout.write(f'Created student: {student.first_name} {student.last_name} in {standard}')
                
                # 5. Create subjects for each standard
                subject_names = [
                    'Mathematics', 'English', 'Science', 'Social Studies', 'Art', 
                    'Physical Education', 'Music', 'Creative Writing', 'Religious Instruction'
                ]
                
                for standard in standards:
                    # Assign a teacher to this standard
                    standard_teacher = random.choice(teachers)
                    
                    # Create subjects for this standard
                    for i in range(min(num_subjects, len(subject_names))):
                        subject_name = subject_names[i]
                        subject, _ = Subject.objects.get_or_create(
                            name=subject_name,
                            defaults={'description': f'Study of {subject_name}'}
                        )
                        
                        standard_subject = StandardSubject.objects.create(
                            standard=standard,
                            subject=subject,
                            teacher=standard_teacher,
                            year=current_year
                        )
                        self.stdout.write(f'Created subject {subject.name} for {standard}')
                        
                        # 6. Create tests for each term
                        for term in [1, 2, 3]:
                            for t in range(num_tests):
                                test_type = random.choice(TEST_TYPE_CHOICES)[0]
                                test_date = self.fake.date_this_year()
                                
                                test = Test.objects.create(
                                    standard=standard,
                                    year=current_year,
                                    term=term,
                                    test_type=test_type,
                                    test_date=test_date,
                                    description=f'{test_type.replace("_", " ").title()} Test {t+1}',
                                    created_by=standard_teacher
                                )
                                
                                # Create test subject
                                test_subject = TestSubject.objects.create(
                                    test=test,
                                    standard_subject=standard_subject,
                                    max_score=100
                                )
                                
                                # 7. Add scores for each student
                                students = Student.objects.filter(standard=standard)
                                for student in students:
                                    score = random.randint(40, 100)
                                    TestScore.objects.create(
                                        test_subject=test_subject,
                                        student=student,
                                        score=score
                                    )
                                
                                self.stdout.write(f'Created test {test} with scores for {len(students)} students')
        
        self.stdout.write(self.style.SUCCESS('Demo data generation completed successfully!'))
