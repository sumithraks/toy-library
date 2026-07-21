from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.ADMIN
        )


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "member", None)
        return owner == request.user
