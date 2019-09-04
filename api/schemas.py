from core.schemas import ResponsesSchema, SimpleCreatorSchema, SimpleActionSchema
from core.schemas import ResponsesNoInputSchema, SimpleNoInputCreatorSchema, SimpleNoInputActionSchema


class PartnerUpdateSchema(SimpleCreatorSchema):
    """
    Класс документирует partner-update
    (добавляет статус коды в openapi документацию)
    """
    pass


class UserLoginSchema(SimpleActionSchema):
    pass


class CaptchaInfoSchema(ResponsesSchema):

    status_description = {
        '200': 'Done',
    }

