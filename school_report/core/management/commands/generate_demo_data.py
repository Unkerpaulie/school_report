import random
import json
import os
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.db import transaction

from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import SchoolYear, Term, SchoolStaff, StandardTeacher, SchoolEnrollment, StandardEnrollment, StandardSubject
from core.utils import get_current_year_and_term

class Command(BaseCommand):
    help = 'Generate comprehensive demo data for the school reporting system'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker()
        self.usernames = set()  # Track used usernames
        self.school_users = []  # Track users for JSON output

    def add_arguments(self, parser):
        parser.add_argument('--schools', type=int, default=1, help='Number of schools to create')
        # parser.add_argument('--groups', type=int, default=1, help='Number of groups per standard')
        parser.add_argument('--students-per-class', type=int, default=None, help='Number of students per class (random 13-18 if not specified)')
        parser.add_argument('--output-dir', type=str, default='try', help='Directory to save user info JSON files')

    def generate_phone_number(self):
        """Generate a Trinidad & Tobago phone number"""
        return f"(868) {random.choice([2, 3, 4, 6, 7])}{str(random.randint(0, 99)).zfill(2)}-{str(random.randint(0, 9999)).zfill(4)}"

    def generate_unique_username(self, first_name, last_name):
        """Generate a unique username based on first and last name"""
        base_username = f"{first_name[0].lower()}{last_name.lower()}"[:15]
        username = base_username
        counter = 2

        while username in self.usernames or User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"[:15]
            counter += 1

        self.usernames.add(username)
        return username

    def create_person_name(self):
        """Generate a random person's name with gender-specific title"""
        male_titles = ['Mr', 'Dr', 'Prof']
        female_titles = ['Mrs', 'Ms', 'Dr', 'Prof']
        if random.random() < 0.5:
            title = random.choice(male_titles)
            first_name = self.fake.first_name_male()
            last_name = self.fake.last_name()
        else:
            title = random.choice(female_titles)
            first_name = self.fake.first_name_female()
            last_name = self.fake.last_name()

        return first_name, last_name, title

    def create_user(self, first_name, last_name, user_type, title=None, position=None):
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

        # Update profile (automatically created via signals)
        profile = user.profile
        profile.user_type = user_type
        profile.phone_number = self.generate_phone_number()
        profile.must_change_password = True

        # Set title if provided
        if title:
            profile.title = title

        # Set position for admin staff
        if position and user_type == 'administration':
            profile.position = position

        profile.save()

        # Track user for JSON output
        self.school_users.append({
            'full_name': profile.get_full_name(),
            'username': username,
            'user_type': user_type,
            'position': position if position else 'N/A'
        })

        return user

    def get_school_standards(self, school):
        """Get the automatically created standards for the school"""
        standards = Standard.objects.filter(school=school).order_by('name')
        self.stdout.write(f'📚 Using {standards.count()} automatically created standards:')
        for standard in standards:
            self.stdout.write(f'   - {standard.get_display_name()}')
        return standards

    def create_students_for_standard(self, school, standard, current_year, num_students):
        """Create students and enroll them in the given standard"""
        # Age mapping for Caribbean primary school standards
        age_mapping = {
            'INF1': (5, 6), 
            'INF2': (6, 7), 
            'STD1': (7, 8), 
            'STD2': (8, 9), 
            'STD3': (9, 10), 
            'STD4': (10, 11), 
            'STD5': (11, 12),
        }

        min_age, max_age = age_mapping.get(standard.name, (8, 9))  # Default fallback

        students = []
        for _ in range(num_students):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            # Age appropriate for the standard
            dob = self.fake.date_of_birth(minimum_age=min_age, maximum_age=max_age)

            student = Student.objects.create(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                contact_email=self.fake.email(),
                contact_phone=self.generate_phone_number(),
                parent_name=f"{self.fake.first_name()} {last_name}" if random.random() < 0.8 else f"{self.fake.first_name()} {self.fake.last_name()}"
            )

            # First, enroll student in the school (persistent relationship)
            # Get the first term's start date or use a default date
            enrollment_date = current_year.terms.first().start_date if current_year.terms.exists() else date(current_year.start_year, 9, 1)
            SchoolEnrollment.objects.create(
                school=school,
                student=student,
                enrollment_date=enrollment_date,
                is_active=True
            )

            # Then, assign student to the class for this year
            StandardEnrollment.objects.create(
                year=current_year,
                standard=standard,
                student=student
            )

            students.append(student)
            self.stdout.write(f'Created and enrolled student: {student.first_name} {student.last_name} in {standard}')

        return students

    def create_subjects_for_class(self, teacher, standard, current_year):
        """Create subjects for a teacher's assigned class"""
        # Core subjects for Caribbean primary schools
        subject_names = [
            'Mathematics', 'English Language', 'Science', 'Social Studies',
            'Art & Craft', 'Physical Education', 'Music'
        ]

        # Add additional subjects for higher standards (STD3, STD4, STD5)
        if standard.name in ['STD3', 'STD4', 'STD5']:
            subject_names.extend(['Creative Writing', 'Religious Instruction'])

        subjects = []
        for subject_name in subject_names:
            standard_subject = StandardSubject.objects.create(
                year=current_year,
                standard=standard,
                subject_name=subject_name,
                description=f'{subject_name} for {standard}',
                created_by=teacher
            )
            subjects.append(standard_subject)
            self.stdout.write(f'Created subject: {subject_name} for {standard} (Teacher: {teacher.get_full_name()})')

        return subjects

    def save_user_info_json(self, school, output_dir):
        """Save user information to JSON file"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename based on school name
        school_slug = school.slug
        filename = f"{school_slug}_users.json"
        filepath = os.path.join(output_dir, filename)

        # Prepare user data
        user_data = {
            'school_name': school.name,
            'school_slug': school_slug,
            'generated_date': date.today().isoformat(),
            'users': self.school_users
        }

        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f'User information saved to: {filepath}'))
        return filepath

    def handle(self, *args, **options):
        num_schools = options['schools']
        # groups_per_standard = options['groups']
        students_per_class = options['students_per_class']
        output_dir = options['output_dir']

        self.stdout.write(self.style.SUCCESS('🏫 Starting comprehensive demo data generation...'))

        for school_num in range(num_schools):
            self.school_users = []  # Reset for each school

            with transaction.atomic():
                self.stdout.write(f'\n📚 Creating School {school_num + 1} of {num_schools}')

                # 1. Create Principal
                principal_first_name, principal_last_name, principal_title = self.create_person_name()

                principal_user = self.create_user(
                    principal_first_name,
                    principal_last_name,
                    'principal',
                    title=principal_title
                )

                self.stdout.write(f'👨‍💼 Created principal: {principal_user.profile.get_full_name()}')

                # 2. Create School
                caribbean_cities = ['Port of Spain', 'San Fernando', 'Chaguanas', 'Arima', 'Point Fortin', 'Sangre Grande', 'Tunapuna', 'Penal']
                school_types = ['Government', 'RC', 'Anglican', 'SDA', 'Presbyterian', 'Hindu']

                city = random.choice(caribbean_cities)
                school_type = random.choice(school_types)
                school_name = f"{city} {school_type} Primary School"

                # Randomly choose number of groups (1-3 for demo variety)
                groups_per_standard = random.choice([1, 1, 1, 2, 2, 3])  # Weighted towards 1 group

                school = School.objects.create(
                    name=school_name,
                    principal_user=principal_user,
                    address=f"{random.randint(1, 999)} {self.fake.street_name()}, {city}, Trinidad and Tobago",
                    contact_phone=self.generate_phone_number(),
                    contact_email=f"info@{school_name.lower().replace(' ', '').replace('&', 'and')}.edu.tt",
                    groups_per_standard=groups_per_standard
                )

                self.stdout.write(f'🏫 Created school: {school.name}')

                # 3. Get Current School Year (will auto-create if needed)
                current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)
                self.stdout.write(f'📅 School year: {current_year} (Term: {current_term}, Vacation: {is_on_vacation})')

                # 4. Create SchoolStaff entry for Principal (no longer tied to academic year)
                SchoolStaff.objects.create(
                    school=school,
                    staff=principal_user.profile,
                    position='Principal',
                    is_active=True
                )

                # 5. Get School Standards (automatically created by signal)
                standards = self.get_school_standards(school)

                # 6. Create Administrative Staff (3 positions as specified)
                admin_positions = ['Vice Principal', 'Secretary', 'Administrative Assistant']
                admin_staff = []

                for position in admin_positions:
                    first_name, last_name, title = self.create_person_name()

                    admin_user = self.create_user(
                        first_name,
                        last_name,
                        'administration',
                        title=title,
                        position=position
                    )

                    # Create SchoolStaff entry
                    SchoolStaff.objects.create(
                        school=school,
                        staff=admin_user.profile,
                        position=position,
                        is_active=True
                    )

                    admin_staff.append(admin_user.profile)
                    self.stdout.write(f'👩‍💼 Created admin staff: {admin_user.profile.get_full_name()} ({position})')

                # 7. Create Teachers and Assign to Classes (one teacher per standard/group)
                teachers = []
                for i, standard in enumerate(standards):
                    first_name, last_name, title = self.create_person_name()

                    teacher_user = self.create_user(
                        first_name,
                        last_name,
                        'teacher',
                        title=title
                    )

                    # Create SchoolStaff entry (no longer tied to academic year)
                    SchoolStaff.objects.create(
                        school=school,
                        staff=teacher_user.profile,
                        position='Teacher',
                        is_active=True
                    )

                    # Assign teacher to this standard using new historical system
                    StandardTeacher.objects.create(
                        year=current_year,
                        standard=standard,
                        teacher=teacher_user.profile
                    )

                    teachers.append(teacher_user.profile)
                    self.stdout.write(f'👨‍🏫 Created teacher: {teacher_user.profile.get_full_name()} → {standard}')

                # 8. Create Students for Each Class
                total_students = 0
                for i, standard in enumerate(standards):
                    # Determine number of students (random 13-18 if not specified)
                    num_students = students_per_class if students_per_class else random.randint(13, 18)

                    students = self.create_students_for_standard(school, standard, current_year, num_students)
                    total_students += len(students)
                    self.stdout.write(f'👥 Created {len(students)} students for {standard}')

                # 9. Have Teachers Create Subjects for Their Classes
                for i, standard in enumerate(standards):
                    teacher = teachers[i]  # Each teacher corresponds to their standard
                    subjects = self.create_subjects_for_class(teacher, standard, current_year)
                    self.stdout.write(f'📚 Created {len(subjects)} subjects for {standard} (Teacher: {teacher.get_full_name()})')

                # 10. Save User Information to JSON
                json_file = self.save_user_info_json(school, output_dir)

                self.stdout.write(self.style.SUCCESS(f'✅ School {school.name} completed successfully!'))
                self.stdout.write(f'   - Principal: 1')
                self.stdout.write(f'   - Admin Staff: {len(admin_staff)}')
                self.stdout.write(f'   - Teachers: {len(teachers)}')
                self.stdout.write(f'   - Standards: {len(standards)}')
                self.stdout.write(f'   - Students: {total_students}')
                self.stdout.write(f'   - User info saved to: {json_file}')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Demo data generation completed successfully!'))
        self.stdout.write(f'📁 User information files saved in: {output_dir}/')
        self.stdout.write(f'🔑 All users have password: ChangeMe!')
        self.stdout.write(f'📊 Total schools created: {num_schools}')
