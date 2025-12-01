"""
Auditlog and Activity Stream Model Registration
Register all models that should be tracked for audit logging and activity streams.

Auditlog provides a complete technical audit trail for compliance and debugging.
All changes to registered models are automatically logged with:
- User who made the change
- Timestamp
- IP address
- Before/after values for all fields

Activity Stream allows models to be used in activity feeds (actor, action_object, target).
"""

from auditlog.registry import auditlog
from actstream import registry as actstream_registry

# Import all models that need audit tracking
from django.contrib.auth.models import User
from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import (
    SchoolYear, Term, StandardTeacher, SchoolEnrollment, 
    StandardEnrollment, StandardSubject, SchoolStaff, AcademicTransition
)
from reports.models import (
    Test, TestSubject, TestScore, StudentTermReview, StudentSubjectScore
)


# ============================================================================
# CORE MODELS - User accounts and profiles
# ============================================================================
auditlog.register(User, exclude_fields=['last_login', 'password'])
auditlog.register(UserProfile)


# ============================================================================
# SCHOOL MODELS - Schools, standards, and students
# ============================================================================
auditlog.register(School)
auditlog.register(Standard)
auditlog.register(Student)


# ============================================================================
# ACADEMIC MODELS - Years, terms, enrollments, subjects
# ============================================================================
auditlog.register(SchoolYear)
auditlog.register(Term)
auditlog.register(StandardTeacher)
auditlog.register(SchoolEnrollment)
auditlog.register(StandardEnrollment)
auditlog.register(StandardSubject)
auditlog.register(SchoolStaff)
auditlog.register(AcademicTransition)


# ============================================================================
# REPORT MODELS - Tests, scores, and reviews
# ============================================================================
auditlog.register(Test)
auditlog.register(TestSubject)
auditlog.register(TestScore)
auditlog.register(StudentTermReview)
auditlog.register(StudentSubjectScore)


# ============================================================================
# ACTIVITY STREAM REGISTRATION
# Register models that can be used in activity feeds
# ============================================================================

# Register User and UserProfile as actors (who performs actions)
actstream_registry.register(User)
actstream_registry.register(UserProfile)

# Register models that can be action objects or targets
actstream_registry.register(School)
actstream_registry.register(Standard)
actstream_registry.register(Student)
actstream_registry.register(SchoolYear)
actstream_registry.register(Term)
actstream_registry.register(StandardTeacher)
actstream_registry.register(SchoolEnrollment)
actstream_registry.register(StandardEnrollment)
actstream_registry.register(StandardSubject)
actstream_registry.register(Test)
actstream_registry.register(TestSubject)
actstream_registry.register(StudentTermReview)

