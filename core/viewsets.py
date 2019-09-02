# Примеси для сериалайзеров:

class SelectableSerializersMixin(object):
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
        return super(SelectableSerializersMixin, self).get_serializer_class()


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


class ViewSetScopeThrottlesMixin(object):
    """
    Миксин для документирования задания throttles для отдельных действий в ViewSet
    scope throttles должны быть описаны в словаре action_scope_throttles
    Используйте неймспейсы. Например: user.login
    """

    def get_throttles(self):
        if hasattr(self, 'action_scope_throttles'):
            if self.action in self.action_scope_throttles:
                return self.action_scope_throttles[self.action]
        return super(ViewSetScopeThrottlesMixin, self).get_throttles()

class ViewSetQuerysetsMixin(object):
    """
    Миксин для задания queryset действиям в ViewSet
    queryset должны быть заданы в словаре action_querysets
    """

    def get_queryset(self):
        if hasattr(self, 'action_querysets'):
            if self.action in self.action_querysets:
                return self.action_querysets[self.action]
        return super(ViewSetQuerysetsMixin, self).action_querysets()
