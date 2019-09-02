from core.utils import ResponsesSchema, SimpleCreatorSchema, SimpleActionSchema
from core.utils import ResponsesNoInputSchema, SimpleNoInputCreatorSchema, SimpleNoInputActionSchema


class PartnerUpdateSchema(SimpleNoInputCreatorSchema):
    """
    Класс документирует partner-update
    (добавляет статус коды в openapi документацию)
    """
    pass


class UserLoginSchema(SimpleActionSchema):
    pass