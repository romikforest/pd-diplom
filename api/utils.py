from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AcceptAsContentTypeNegotiation(DefaultContentNegotiation):
    """
    Класс устанавливает формат ответа по умолчанию
    такой же, как формат запроса

    """

    def get_accept_list(self, request):
 
        header = request.META.get('HTTP_ACCEPT', '')
        accept_set = { x.strip() for x in header.split(',') if x }
        content_set = { x.strip() for x in request.content_type.split(',') if x }
        common_set = accept_set & content_set
        all_set = {'*/*'}
        if not accept_set or not (accept_set - all_set):
            result = content_set | all_set
        elif common_set and common_set - all_set:
            result = common_set | all_set
        else:
            result = accept_set

        return result

    
# Контроль количества запросов:

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class AnonBurstRateThrottle(AnonRateThrottle):
    scope = 'anon_burst'

class AnonSustainedRateThrottle(AnonRateThrottle):
    scope = 'anon_sustained'
