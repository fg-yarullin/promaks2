from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'TEACHER'

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'STUDENT'

class IsStudentOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['STUDENT', 'TEACHER']

class IsParent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'PARENT'

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'ADMIN'