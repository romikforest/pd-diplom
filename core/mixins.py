# Примеси для сериалайзеров:

class ViewSetViewSerializersMixin(object):
    """
    Миксин выбора сериалайзера отдельно для каждого действия
    Используется с ViewSets.
    Для задания сериалайзеров используйте свойство action_serializers
    Оно должно представлять собой словарь <название действия> - <сериалайзер>
    Если сериалайзер не найден в action_serializers возвращается сериалайзер,
    указанный в свойстве serializer_class
    """

    def get_serializer_class(self):
        if hasattr(self, 'action_serializers'):
            if self.action in self.action_serializers:
                return self.action_serializers[self.action]
        return super(ViewSetViewSerializersMixin, self).get_serializer_class()


class ViewSetViewDescriptionsMixin(object):
    """
    Миксин для документирования actions
    Очень полезен для документирования автоматических и наследуемых действий
    Описания должны быть заданы в словаре action_descriptions
    """

    def get_view_description(self, html=False):
        if hasattr(self, 'action_descriptions'):
            if self.action in self.action_descriptions:
                return self.action_descriptions[self.action]
        return super(ViewSetViewDescriptionsMixin, self).get_view_description(html)


class ViewSetViewScopeThrottlesMixin(object):
    """
    Миксин для документирования задания throttles для отдельных действий в ViewSet
    scope throttles должны быть описаны в словаре action_scope_throttles
    Используйте неймспейсы. Например: user.login
    """

    def get_throttles(self):
        if hasattr(self, 'action_scope_throttles'):
            if self.action in self.action_scope_throttles:
                return self.action_scope_throttles[self.action]
        return super(ViewSetViewScopeThrottlesMixin, self).get_throttles()


class ViewSetViewQuerysetsMixin(object):
    """
    Миксин для задания queryset действиям в ViewSet
    queryset должны быть заданы в словаре action_querysets
    """

    def get_queryset(self):
        if hasattr(self, 'action_querysets'):
            if self.action in self.action_querysets:
                return self.action_querysets[self.action]
        return super(ViewSetViewQuerysetsMixin, self).get_queryset()


class ViewSetViewPermissionsMixin(object):
    """
    Миксин для задания определения permissions для действий в ViewSet
    разрешения должны быть заданы в словаре action_permissions
    """

    def get_permissions(self):
        if hasattr(self, 'action_permissions'):
            if self.action in self.action_permissions:
                return [ permission() for permission in self.action_permissions[self.action]]
        return super(ViewSetViewPermissionsMixin, self).get_permissions()


class SuperSelectableMixin(ViewSetViewSerializersMixin,
                           ViewSetViewDescriptionsMixin,
                           ViewSetViewScopeThrottlesMixin,
                           ViewSetViewQuerysetsMixin,
                           ViewSetViewPermissionsMixin,
                           object
                          ):
    """
    Миксин собирает в себе возможности других миксинов кастомизации данного модуля,
    работающих с полями action_*
    """

    pass
