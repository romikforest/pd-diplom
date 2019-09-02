# Свои схемы для документирования. Краткие. Как пример

from rest_framework.schemas.openapi import AutoSchema 

class PartnerUpdateSchema(AutoSchema):
    """
    Класс документирует partner-update
    (добавляет статус коды в openapi документацию)
    """

    def get_operation(self, path, method, *arg, **kwargs):
        operation = super().get_operation(path, method, *arg, **kwargs)
        # Без подробностей:
        operation['responses'] = {
                '201': { 'description': 'Created!' },
                '400': { 'description': 'Error in input data' },
                '401': { 'description': 'Auth required...' },
                '403': { 'description': 'Forbidden...' },
        }
        return operation