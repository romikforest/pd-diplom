from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from .models import Group as AuthGroup
from .models import User as AuthUser
from .models import ConfirmEmailToken


@admin.register(AuthUser)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = AuthUser

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')


class GroupAdmin(GroupAdmin):
    pass


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)


admin.site.unregister(Group)
admin.site.register(AuthGroup, GroupAdmin)
