from copy import deepcopy
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from rest_auth.models import User

class AccountRegisterAPITests(APITestCase):

    url = reverse('api:user-register')
    data = {
        'first_name': 'SampleFirstName',
        'last_name': 'SampleLastName',
        'email': 'sample@mail.com',
        'company': 'SampleCompany',
        'position': 'SamplePosition',
        'password': 'SamplePassword',
        'password2': 'SamplePassword',
        'recaptcha': 'SampleCaptcha',
        'contacts': []
    }

    def setUp(self):
        # self.job_title = "test job"
        # self.job_description = "lorem ipsum dolor sit amet"
        pass
        

    def try_to_create_user(self, data, format):
        return self.client.post(self.url, data, format=format)


    def try_successful_creation(self, data, format):
        """
        Проверка, что можно зарегистрировать новый аккаунт пользователя
        """

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, format)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn(f'application/{format}', response.accepted_media_type)
        self.assertEqual(User.objects.filter(email=data.get('email')).count(), 1)
        for key, value in data.items():
            if key in ['password', 'password2', 'recaptcha', 'contacts']:
                continue
            self.assertEqual(User.objects.values_list(key, flat=True).get(), value)
        self.assertEqual(User.objects.values_list('is_active', flat=True).get(), False)
        

    def test_create_user_account_json(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт пользователя
        (на входе json)
        """

        self.try_successful_creation(self.data, 'json')


    def test_create_user_account_yaml(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт пользователя
        (на входе yaml)
        """

        data = deepcopy(self.data)
        data.pop('contacts', None)
        self.try_successful_creation(data, 'yaml')


    def test_create_user_account_xml(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт пользователя
        (на входе xml)
        """

        data = deepcopy(self.data)
        data.pop('contacts', None)
        self.try_successful_creation(data, 'xml')

        
    def test_not_equal_password_user_creation_rejected(self):
        """
        Проверка, что попытка создания пользователя при несовпадающих полях password и password2 будет отклонена
        """

        data = deepcopy(self.data)
        data['password'] = 'JxFggg12R4fjzasd123+Q'
        data['password2'] = 'JxFggg12R4fjzasd123+Q2'

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('password', response.data)
        self.assertIn('password2', response.data)

    def test_password_validation_user_creation_rejected(self):
        """
        Проверка, что валидация пароля при создании пользователя
        """

        data = deepcopy(self.data)
        data['password'] = data['password2'] = '1'

        with self.settings(AUTH_PASSWORD_VALIDATORS=settings.NON_DEBUG_PASSWORD_VALIDATORS, RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('password', response.data)
        self.assertIn('password2', response.data)

    
    def test_create_user_with_contacts(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт с контактами
        (на входе json)
        """

        data = deepcopy(self.data)
        phone_contact = {'phone': '+79168008080'}
        address_contact = {'city': 'Moscow', 'street': 'Street', 'house': '1a'}
        data['contacts'] = [ phone_contact, address_contact ]
        
        self.try_successful_creation(data, 'json')

        contacts = User.objects.filter(email=data.get('email'))[0].contacts.all()
        self.assertEqual(contacts.count(), 2)
        if contacts[0].phone == phone_contact['phone']:
            contact1 = contacts[0]
            contact2 = contacts[1]
        else:
            contact1 = contacts[1]
            contact2 = contacts[0]
        self.assertEqual(contact1.phone, phone_contact['phone'])
        self.assertEqual(contact2.city, address_contact['city'])
        self.assertEqual(contact2.street, address_contact['street'])
        self.assertEqual(contact2.house, address_contact['house'])

    
    def test_create_user_with_wrong_contacts_rejected(self):
        """
        Проверка, что нельзя зарегистрировать новый аккаунт с контактом, у которого не указаны необходимые поля
        (на входе json)
        """

        data = deepcopy(self.data)
        data['contacts'] = [ {'city': 'Moscow', 'street': 'Street'} ]

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('contacts', response.data)


class PartnerAccountRegisterAPITests(AccountRegisterAPITests):
    
    url = reverse('api:partner-register')
