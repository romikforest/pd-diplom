from copy import deepcopy
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError
from django.db.utils import Error as DBError, ConnectionDoesNotExist
from django.urls import reverse
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from rest_auth.models import User, ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT

class AccountsAPITests(APITestCase):
    """
    Тесты эндпойнтов для работы с аккаунтами покупателей
    """

    user_type = 'buyer'

    url = reverse('api:user-register')
    confirm_url = reverse('api:user-confirm')
    login_url = reverse('api:user-login')
    password_reset_url = reverse('api:user-password-reset')
    password_reset_confirm_url = reverse('api:user-password-reset-confirm')
    captcha_url = reverse('api:user-captcha')
    list_url = reverse('api:user-list')
    details_url = reverse('api:user-details')

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

    def create_user(self):
        data = deepcopy(self.data)
        contact_data = data.pop('contacts', [])
        password = data.pop('password')
        data.pop('password2')
        data.pop('recaptcha')
            
        user = User.objects.create(**data, type=self.user_type)
        user.is_active = True
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact)
            except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                break

        user.save()
        

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
        self.assertEqual(User.objects.values_list('type', flat=True).get(), self.user_type)
        

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
        Проверка, что происходит валидация пароля при создании пользователя
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

    def test_email_validation_user_creation_rejected(self):
        """
        Проверка, что происходит валидация email при создании пользователя
        """

        data = deepcopy(self.data)
        data['email'] = 'newmail'

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('email', response.data)

    
    def test_user_creation_with_contacts(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт с контактами
        (на входе json)
        """

        data = deepcopy(self.data)
        phone_contact = {'phone': '+79168008080'}
        address_contact = {'city': 'Moscow', 'street': 'Street', 'house': '1a'}
        data['contacts'] = [ phone_contact, address_contact ]
        
        self.try_successful_creation(data, 'json')

        contacts = User.objects.get(email=data.get('email')).contacts.all()
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

    
    def test_user_creation_with_wrong_contacts_is_rejected(self):
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


    def try_request_without_required_field(self, field):
        """
        Проверка, что field - обязательное поле
        """

        data = deepcopy(self.data)
        data.pop(field)

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn(field, response.data)


    def test_first_name_required(self):
        """
        Проверка, что first_name - обязательное поле
        """
        self.try_request_without_required_field('first_name')


    def test_last_name_required(self):
        """
        Проверка, что last_name - обязательное поле
        """
        self.try_request_without_required_field('last_name')


    def test_company_required(self):
        """
        Проверка, что company - обязательное поле
        """
        self.try_request_without_required_field('company')


    def test_position_required(self):
        """
        Проверка, что position - обязательное поле
        """
        self.try_request_without_required_field('position')


    def test_recaptcha_required(self):
        """
        Проверка, что recaptcha - обязательное поле
        """
        self.try_request_without_required_field('recaptcha')


    def test_password_required(self):
        """
        Проверка, что password - обязательное поле
        """
        self.try_request_without_required_field('password')


    def test_password2_required(self):
        """
        Проверка, что password2 - обязательное поле
        """
        self.try_request_without_required_field('password2')


    def test_user_confirm(self):
        """
        Проверка, что подтверждение аккаунта проходит успешно
        """
        self.try_successful_creation(self.data, 'json')
        
        email = self.data['email']
        token = ConfirmEmailToken.objects.get(user__email=email).key
        confirm_data = dict(email=email, token=token)
        response = self.client.post(self.confirm_url, confirm_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)


    def test_confirm_with_random_token_rejected(self):
        """
        Проверка, что подтверждение аккаунта со случайным токеном отклоняется
        """
        self.try_successful_creation(self.data, 'json')
        
        email = self.data['email']
        token = '123'
        confirm_data = dict(email=email, token=token)
        response = self.client.post(self.confirm_url, confirm_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)

    
    def test_confirm_without_email_rejected(self):
        """
        Проверка, что подтверждение аккаунта без указания email отклоняется
        """
        self.try_successful_creation(self.data, 'json')
        
        email = self.data['email']
        token = ConfirmEmailToken.objects.get(user__email=email).key
        confirm_data = dict(token=token)
        response = self.client.post(self.confirm_url, confirm_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('email', response.data)
        self.assertIn('application/json', response.accepted_media_type)


    def test_confirm_without_token_rejected(self):
        """
        Проверка, что подтверждение аккаунта без указания токена отклоняется
        """
        self.try_successful_creation(self.data, 'json')
        
        email = self.data['email']
        confirm_data = dict(email=email)
        response = self.client.post(self.confirm_url, confirm_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('token', response.data)
        self.assertIn('application/json', response.accepted_media_type)


    def test_user_login(self):
        """
        Проверка, что вход пользователя проходит успешно
        """

        self.create_user()
        
        email = self.data['email']
        password = self.data['password']
        recaptcha = self.data['recaptcha']

        login_data = dict(email=email, password=password, recaptcha=recaptcha)
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('token', response.data)
        self.assertIn('application/json', response.accepted_media_type)


    def try_user_login_without_required_field(self, field):
        """
        Проверка, что вход пользователя отклоняется, если не указано обязательное поле
        """

        self.create_user()
        
        email = self.data['email']
        password = self.data['password']
        recaptcha = self.data['recaptcha']

        login_data = dict(email=email, password=password, recaptcha=recaptcha)
        login_data.pop(field, None)
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(field, response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('token', response.data)


    def test_user_login_without_email_reject(self):
        """
        Проверка, что вход пользователя отклоняется, если не указан email
        """
        self.try_user_login_without_required_field('email')


    def test_user_login_without_password_reject(self):
        """
        Проверка, что вход пользователя отклоняется, если не указан password
        """
        self.try_user_login_without_required_field('password')


    def test_user_login_without_recaptcha_reject(self):
        """
        Проверка, что вход пользователя отклоняется, если не указан recaptcha
        """
        self.try_user_login_without_required_field('recaptcha')


    def test_user_login_with_wrong_password_rejected(self):
        """
        Проверка, что вход пользователя отклоняется, если не указан неверный пароль
        """

        self.create_user()
        
        email = self.data['email']
        password = '1'
        recaptcha = self.data['recaptcha']

        login_data = dict(email=email, password=password, recaptcha=recaptcha)
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('token', response.data)


    def test_password_reset(self):
        """
        Проверка, что пользователь может сбросить пароль
        """

        self.create_user()
        
        email = self.data['email']
        password = self.data['password']

        user = User.objects.get(email=email)

        reset_data = dict(email=email)
        response = self.client.post(self.password_reset_url, reset_data, format='json', HTTP_USER_AGENT='test client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'OK')
        self.assertIn('application/json', response.accepted_media_type)

        reset_confirm_data = dict(password=password, token=ResetPasswordToken.objects.get(user_id=user.id).key)
        response = self.client.post(self.password_reset_confirm_url, reset_confirm_data, format='json', HTTP_USER_AGENT='test client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'OK')
        self.assertIn('application/json', response.accepted_media_type)

    
    def test_get_captcha(self):
        """
        Проверка, что можно получить публичный ключ капчи
        """
        response = self.client.get(self.captcha_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('public_key', response.data)


    def test_user_list(self):
        """
        Проверка, что авторизированный пользователь может просмотреть список пользователей
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get(self.list_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertNotIn('Status', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)


    def test_user_list_anonymous_rejected(self):
        """
        Проверка, что не авторизированный пользователь не может просмотреть список пользователей
        """

        self.create_user()
        email = self.data['email']
        user = User.objects.get(email=email)

        response = self.client.get(self.list_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)


    def test_user_retrieve(self):
        """
        Проверка, что авторизированный пользователь может просмотреть данные пользователя
        """

        self.create_user()
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get(f'{self.list_url}/{user.id}', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertNotIn('Status', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('url', response.data)
        self.assertIn('id', response.data)
        self.assertIn('first_name', response.data)
        self.assertIn('last_name', response.data)
        self.assertIn('email', response.data)
        self.assertIn('company', response.data)
        self.assertIn('position', response.data)
        self.assertIn('contacts', response.data)


    def test_user_retrieve_anonympus_rejected(self):
        """
        Проверка, что не авторизированный пользователь не может просмотреть данные пользователя
        """

        self.create_user()
        email = self.data['email']
        user = User.objects.get(email=email)

        response = self.client.get(f'{self.list_url}/{user.id}', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)


    def test_user_details(self):
        """
        Проверка, что авторизированный пользователь может просмотреть свои данные
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get(self.details_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertNotIn('Status', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('url', response.data)
        self.assertIn('id', response.data)
        self.assertIn('first_name', response.data)
        self.assertEqual(response.data['first_name'], self.data['first_name'])
        self.assertIn('last_name', response.data)
        self.assertEqual(response.data['last_name'], self.data['last_name'])
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'], self.data['email'])
        self.assertIn('company', response.data)
        self.assertEqual(response.data['company'], self.data['company'])
        self.assertIn('position', response.data)
        self.assertEqual(response.data['position'], self.data['position'])
        self.assertIn('contacts', response.data)
        self.assertEqual(len(response.data['contacts']), len(self.data['contacts']))


    def test_user_details_anonymous_rejected(self):
        """
        Проверка, что не авторизированный пользователь не может просмотреть свои данные
        """

        self.create_user()
        email = self.data['email']
        user = User.objects.get(email=email)

        response = self.client.get(self.details_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)


    def try_user_details_put(self, field, value):
        """
        Проверка, что авторизированный пользователь может изменить поле своих данных
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.put(self.details_url, data={field: value}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)

        if field != 'email':
            email = self.data['email']
        else:
            email = value
        self.assertEqual(User.objects.values_list(field, flat=True).get(email=email), value)


    def test_user_details_put_first_name(self):
        """
        Проверка, что авторизированный пользователь может изменить свой first_name
        """
        self.try_user_details_put('first_name', 'NewValue')


    def test_user_details_put_last_name(self):
        """
        Проверка, что авторизированный пользователь может изменить свой last_name
        """
        self.try_user_details_put('last_name', 'NewValue')


    def test_user_details_put_email(self):
        """
        Проверка, что авторизированный пользователь может изменить свой email
        """
        self.try_user_details_put('email', 'newmail@mail.com')


    def test_user_details_put_company(self):
        """
        Проверка, что авторизированный пользователь может изменить свой company
        """
        self.try_user_details_put('company', 'NewValue')


    def test_user_details_put_position(self):
        """
        Проверка, что авторизированный пользователь может изменить свой position
        """
        self.try_user_details_put('position', 'NewValue')


    def test_user_details_put_anonymous_rejected(self):
        """
        Проверка, что не авторизированный пользователь не может изменить поле своих данных
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)

        response = self.client.put(self.details_url, data={'first_name': 'NewValue'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)


    def test_user_details_put_email_validation(self):
        """
        Проверка, что происходит валидация email при попытке изменения данных
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.put(self.details_url, data={'email': 'newmail'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)


    def test_user_details_put_password(self):
        """
        Проверка, что авторизированный пользователь может изменить пароль
        """

        self.create_user()
        
        new_password = '1-'
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        with self.settings(AUTH_PASSWORD_VALIDATORS=[]):
            response = self.client.put(self.details_url, data={'password': new_password}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)

        user = authenticate(username=email, password=new_password)
        self.assertTrue(user)


    def test_user_details_put_password_validation(self):
        """
        Проверка, что при попытке смены пароля происходит его валидация
        """

        self.create_user()
        
        new_password = '1-'
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        with self.settings(AUTH_PASSWORD_VALIDATORS=settings.NON_DEBUG_PASSWORD_VALIDATORS):
            response = self.client.put(self.details_url, data={'password': new_password}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

    def test_user_creation_with_too_many_contacts(self):
        """
        Проверка, что нельзя зарегистрировать новый аккаунт со слишком большим числом контактов
        (на входе json)
        """

        data = deepcopy(self.data)
        data['contacts'] = [ {'phone': '+79168008080'} ] * (ADDRESS_ITEMS_LIMIT + 1)

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contacts', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)


    def test_user_creation_with_almost_too_many_contacts(self):
        """
        Проверка, что можно зарегистрировать новый аккаунт с максимальным числом контактов
        (на входе json)
        """

        data = deepcopy(self.data)
        data['contacts'] = [ {'phone': '+79168008080'} ] * ADDRESS_ITEMS_LIMIT

        with self.settings(AUTH_PASSWORD_VALIDATORS=[], RECAPTCHA_TESTING=True):
            response = self.try_to_create_user(data, 'json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)

    def test_user_details_put_almost_too_many_contacts(self):
        """
        Проверка, что авторизированный пользователь может добавить максимальное число контактов
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        data = deepcopy(self.data)
        data['contacts'] = [ {'phone': '+79168008080'} ] * ADDRESS_ITEMS_LIMIT

        response = self.client.put(self.details_url, data=data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('contacts', response.data)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)

    def test_user_details_put_too_many_contacts(self):
        """
        Проверка, что авторизированный пользователь не может добавить слишком много контактов
        """

        self.create_user()
        
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        data = deepcopy(self.data)
        data['contacts'] = [ {'phone': '+79168008080'} ] * (ADDRESS_ITEMS_LIMIT + 1)

        response = self.client.put(self.details_url, data=data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contacts', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        


class PartnerAccountsAPITests(AccountsAPITests):
    """
    Тесты эндпойнтов для работы с аккаунтами поставщиков 
    """
    
    url = reverse('api:partner-register')
    confirm_url = reverse('api:partner-confirm')
    login_url = reverse('api:partner-login')
    password_reset_url = reverse('api:partner-password-reset')
    password_reset_confirm_url = reverse('api:partner-password-reset-confirm')
    captcha_url = reverse('api:partner-captcha')
    list_url = reverse('api:partner-list')
    details_url = reverse('api:partner-details')

    user_type = 'shop'
