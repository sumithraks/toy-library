import pytest

from apps.common.factories import UserFactory

from . import services
from .models import User


@pytest.mark.django_db
class TestCreateStaffUser:
    def test_creates_staff_role_with_the_given_password(self):
        user = services.create_staff_user("newstaff@example.com", "startpass123", "New", "Staff")

        assert user.role == User.Role.STAFF
        assert user.is_staff is True
        assert user.is_email_verified is True
        assert user.has_usable_password() is True
        assert user.check_password("startpass123") is True


@pytest.mark.django_db
class TestSetStaffRole:
    def test_admin_promotes_staff_to_admin(self):
        admin = UserFactory(is_staff=True, role=User.Role.ADMIN)
        staff = UserFactory(is_staff=True, role=User.Role.STAFF)

        services.set_staff_role(staff, User.Role.ADMIN, admin)
        staff.refresh_from_db()

        assert staff.role == User.Role.ADMIN
        assert staff.is_staff is True

    def test_cannot_change_own_role(self):
        admin = UserFactory(is_staff=True, role=User.Role.ADMIN)

        with pytest.raises(ValueError, match="cannot change your own role"):
            services.set_staff_role(admin, User.Role.STAFF, admin)

    def test_cannot_change_role_of_a_member(self):
        admin = UserFactory(is_staff=True, role=User.Role.ADMIN)
        member = UserFactory()

        with pytest.raises(ValueError, match="Only STAFF or ADMIN"):
            services.set_staff_role(member, User.Role.ADMIN, admin)

    def test_cannot_change_role_of_a_deactivated_account(self):
        admin = UserFactory(is_staff=True, role=User.Role.ADMIN)
        staff = UserFactory(is_staff=True, role=User.Role.STAFF, is_active=False)

        with pytest.raises(ValueError, match="deactivated account"):
            services.set_staff_role(staff, User.Role.ADMIN, admin)


@pytest.mark.django_db
class TestDeactivateReactivateStaffUser:
    def test_deactivate_and_reactivate_staff_user(self):
        staff = UserFactory(is_staff=True, role=User.Role.STAFF)

        services.deactivate_staff_user(staff)
        staff.refresh_from_db()
        assert staff.is_active is False

        services.reactivate_staff_user(staff)
        staff.refresh_from_db()
        assert staff.is_active is True

    def test_cannot_deactivate_a_member(self):
        member = UserFactory()

        with pytest.raises(ValueError, match="Only STAFF or ADMIN"):
            services.deactivate_staff_user(member)
