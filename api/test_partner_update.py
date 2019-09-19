from copy import deepcopy
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError
from django.db.utils import Error as DBError, ConnectionDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
import os
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIRequestFactory, APILiveServerTestCase

from rest_auth.models import User
from core.models import Category, ProductInfo, Parameter, ProductParameter
from core.partner_info_loader import load_partner_info

class PartnerUpdateTests(APILiveServerTestCase):
    """
    Тесты обновления прайсов поставщика
    """

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


    def create_user(self, email=None):
        """
        Создание пользователя
        """
        from copy import deepcopy
        data = deepcopy(self.data)
        data['email'] = email or self.data['email']
        contact_data = data.pop('contacts', [])
        password = data.pop('password')
        data.pop('password2')
        data.pop('recaptcha')
            
        user = User.objects.create(**data, type='shop')
        user.is_active = True
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact)
            except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                break

        user.save()


    def try_partner_update_url(self, format, email=None):
        """
        Загрузить информацию поставщика по url
        """

        email = email or self.data['email']

        self.create_user(email)
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')       

        response = self.client.post(reverse('api:partner-update'),
                                    data={'url': self.live_server_url + reverse('api:test_url', kwargs={'ext': format})},
                                    format='json')

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertTrue(Category.objects.count())
        self.assertTrue(Parameter.objects.count())
        self.assertTrue(ProductInfo.objects.count())
        self.assertTrue(ProductParameter.objects.count()) 


    def try_partner_update_url_wrong(self, format, email=None, error_code=status.HTTP_400_BAD_REQUEST, check_db_is_empty=True):
        """
        Загрузить информацию поставщика по url с некорректным содержимым
        """

        email = email or self.data['email']
        self.create_user(email)
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')       

        response = self.client.post(reverse('api:partner-update'),
                                    data={'url': self.live_server_url + reverse('api:test_url', kwargs={'ext': format})},
                                    format='json')

        # print(response.data)

        self.assertEqual(response.status_code, error_code)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        if check_db_is_empty:
            self.assertFalse(Category.objects.count())
            self.assertFalse(Parameter.objects.count())
            self.assertFalse(ProductInfo.objects.count())
            self.assertFalse(ProductParameter.objects.count())


    def try_partner_update_file(self, format, check_parameters=True):
        """
        Загрузить информацию поставщика из файла
        """

        self.create_user()
        email = self.data['email']
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        with open(os.path.join(settings.MEDIA_ROOT, f'tests/shop1.{format}'), 'rb') as fp:
            response = self.client.post(reverse('api:partner-update'),
                                        data=encode_multipart(BOUNDARY, {'file': fp}), 
                                        content_type=MULTIPART_CONTENT)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertTrue(Category.objects.count())
        self.assertTrue(ProductInfo.objects.count())
        if check_parameters:
            self.assertTrue(Parameter.objects.count())
            self.assertTrue(ProductParameter.objects.count())


    def try_partner_update_file_wrong(self, format, email=None, error_code=status.HTTP_400_BAD_REQUEST, check_db_is_empty=True):
        """
        Загрузить информацию поставщика из файла с некорректным содержимым
        """

        email = email or self.data['email']
        self.create_user(email)
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        with open(os.path.join(settings.MEDIA_ROOT, f'tests/shop1.{format}'), 'rb') as fp:
            response = self.client.post(reverse('api:partner-update'),
                                        data=encode_multipart(BOUNDARY, {'file': fp}), 
                                        content_type=MULTIPART_CONTENT)

        self.assertEqual(response.status_code, error_code)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        if check_db_is_empty:
            self.assertFalse(Category.objects.count())
            self.assertFalse(Parameter.objects.count())
            self.assertFalse(ProductInfo.objects.count())
            self.assertFalse(ProductParameter.objects.count())

    def test_not_shop_owner_update(self):
        """
        Нельзя загрузить информацию по ужому магазину
        """
        self.try_partner_update_url('json')
        self.try_partner_update_url_wrong('json', email='sample2@mail.com', error_code=status.HTTP_403_FORBIDDEN, check_db_is_empty=False) 


    def test_partner_update_file_json(self):
        """
        Загрузить информацию поставщика из файла json
        """
        self.try_partner_update_file('json')


    def test_partner_update_file_yaml(self):
        """
        Загрузить информацию поставщика из файла yaml
        """
        self.try_partner_update_file('yaml')


    def test_partner_update_file_xml(self):
        """
        Загрузить информацию поставщика из файла xml
        """
        self.try_partner_update_file('xml')

    def test_partner_update_url_json(self):
        """
        Загрузить информацию поставщика по url json
        """
        self.try_partner_update_url('json')

    def test_partner_update_url_yaml(self):
        """
        Загрузить информацию поставщика по url yaml
        """
        self.try_partner_update_url('yaml')

    def test_partner_update_url_xml(self):
        """
        Загрузить информацию поставщика по url xml
        """
        self.try_partner_update_url('xml')

    def test_partner_update_url_wrong_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong.json')

    def test_partner_update_file_wrong_json(self):
        """
        Тест, что нельзя загрузить некорректный файл json
        """
        self.try_partner_update_file_wrong('wrong.json')

    def test_partner_update_url_wrong2_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong2.json')

    def test_partner_update_url_wrong3_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong3.json')

    def test_partner_update_url_wrong_ddd(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong.ddd')

    def test_partner_update_url_wrong4_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong4.json')

    def test_partner_update_url_wrong5_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong5.json')

    def test_partner_update_url_wrong6_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong6.json')

    def test_partner_update_url_wrong7_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong7.json')

    def test_partner_update_url_wrong8_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong8.json')

    def test_partner_update_url_wrong9_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong9.json')

    def test_partner_update_url_wrong10_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong10.json')

    def test_partner_update_url_wrong11_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong11.json')

    def test_partner_update_url_wrong12_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong12.json')

    def test_partner_update_url_wrong13_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong13.json')

    def test_partner_update_url_wrong14_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong14.json')

    def test_partner_update_url_wrong15_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong15.json')

    def test_partner_update_url_wrong16_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong16.json')

    def test_partner_update_url_wrong17_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong17.json')

    def test_partner_update_url_wrong18_json(self):
        """
        Тест, что нельзя загрузить некорректный json по url
        """
        self.try_partner_update_url_wrong('wrong18.json')


    def test_partner_update_url_wrong_url(self):
        """
        Тест, некорректный url
        """
        email = self.data['email']
        self.create_user(email)
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')       

        response = self.client.post(reverse('api:partner-update'),
                                    data={'url': 'ggg'},
                                    format='json')

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertFalse(Category.objects.count())
        self.assertFalse(Parameter.objects.count())
        self.assertFalse(ProductInfo.objects.count())
        self.assertFalse(ProductParameter.objects.count())


    def test_partner_update_url_wrong_url_direct(self):
        """
        Тест, некорректный url (прямой тест функции)
        """
        response = load_partner_info(url='ggg')

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertFalse(Category.objects.count())
        self.assertFalse(Parameter.objects.count())
        self.assertFalse(ProductInfo.objects.count())
        self.assertFalse(ProductParameter.objects.count())


    def test_partner_update_url_404_url_direct(self):
        """
        Тест, url не найден
        """
        response = load_partner_info(url=self.live_server_url + reverse('api:test_url', kwargs={'ext': 'nonreal.json'}))

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertFalse(Category.objects.count())
        self.assertFalse(Parameter.objects.count())
        self.assertFalse(ProductInfo.objects.count())
        self.assertFalse(ProductParameter.objects.count())


    def test_partner_update_no_arguments(self):
        """
        Не указаны аргументы
        """
        email = self.data['email']
        self.create_user(email)
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')       

        response = self.client.post(reverse('api:partner-update'),
                                    data={},
                                    format='json')

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)
        self.assertIn('file', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertFalse(Category.objects.count())
        self.assertFalse(Parameter.objects.count())
        self.assertFalse(ProductInfo.objects.count())
        self.assertFalse(ProductParameter.objects.count())

    def test_partner_update_no_arguments_direct(self):
        """
        Не указаны аргументы
        """     

        response = load_partner_info()

        # print(response.data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertFalse(Category.objects.count())
        self.assertFalse(Parameter.objects.count())
        self.assertFalse(ProductInfo.objects.count())
        self.assertFalse(ProductParameter.objects.count())

    def test_partner_update_no_product_parameters(self):
        """
        Загрузить информацию поставщика по url при отсутствии описаний параметров
        """

        self.try_partner_update_file('noparams.json', check_parameters=False)
