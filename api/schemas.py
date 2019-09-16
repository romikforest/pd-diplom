from django.utils.translation import gettext_lazy as t

from core.schemas import ResponsesSchema


class PartnerUpdateSchema(ResponsesSchema):
    """
    Класс документирует partner-update
    (добавляет статус коды в openapi документацию)
    """
    status_descriptions = {
        '201': t('Created'),
        '404': t('URL не найден'),
    }


class UserRegisterSchema(ResponsesSchema):
    """
    Класс документирует user-register и partner-register
    (добавляет статус коды в openapi документацию)
    """
    status_descriptions_create = {
        '201': t('Пользователь создан'),
    }

    def get_status_descriptions(self, has_body=False, *args, **kwargs):
        results = super().get_status_descriptions(has_body, *args, **kwargs)
        if self.view.action == 'create':
            results.update(self.status_descriptions_create)
        return results


class OrderCreateSchema(ResponsesSchema):
    """
    Класс документирует order-create
    (добавляет статус коды в openapi документацию)
    """
    status_descriptions_create = {
        '409': t('Корзина пуста'),
    }
