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

