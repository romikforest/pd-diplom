from copy import deepcopy
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError
from django.db.utils import Error as DBError, ConnectionDoesNotExist
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
import os
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.models import ProductInfo, Shop, Category, Order
from core.utils import is_dict, is_list
from rest_auth.models import User, Contact

class APITests(APITestCase):
    """
    Тесты эндпойнтов API (кроме эндпойнтов по работе с аккаунтами пользователей
    и обновлению прайсов поставщика)
    """

    buyer1_data = {
        'first_name': 'Buyer1FirstName',
        'last_name': 'Buyer1LastName',
        'email': 'Buyer1@mail.com',
        'company': 'Buyer1Company',
        'position': 'Buyer1Position',
        'password': 'Buyer1Password',
        'password2': 'Buyer1Password',
        'recaptcha': 'Buyer1Captcha',
        'type': 'buyer',
        'contacts': [
            {'phone': '+79168008080', 'person': 'OldPerson', 'city': 'Big'},
            {'city': 'Moscow', 'street': 'Street', 'house': '1a'},
        ]
    }

    buyer2_data = {
        'first_name': 'Buyer2FirstName',
        'last_name': 'Buyer2LastName',
        'email': 'Buyer2@mail.com',
        'company': 'Buyer2Company',
        'position': 'Buyer2Position',
        'password': 'Buyer2Password',
        'password2': 'Buyer2Password',
        'recaptcha': 'Buyer2Captcha',
        'type': 'buyer',
        'contacts': []
    }

    shop_owner1_data = {
        'first_name': 'Shop1FirstName',
        'last_name': 'Shop1LastName',
        'email': 'Shop1@mail.com',
        'company': 'Shop1Company',
        'position': 'Shop1Position',
        'password': 'Shop1Password',
        'password2': 'Shop1Password',
        'recaptcha': 'Shop1Captcha',
        'type': 'shop',
        'contacts': [
            {'phone': '+79168008080'},
            {'city': 'Moscow', 'street': 'Street', 'house': '1a'},
        ]
    }

    shop_owner2_data = {
        'first_name': 'Shop2FirstName',
        'last_name': 'Shop2LastName',
        'email': 'Shop2@mail.com',
        'company': 'Shop2Company',
        'position': 'Shop2Position',
        'password': 'Shop2Password',
        'password2': 'Shop2Password',
        'recaptcha': 'Shop2Captcha',
        'type': 'shop',
        'contacts': []
    }

    def create_user(self, data):
        """
        Создание пользователя
        """
        data = deepcopy(data)
        contact_data = data.pop('contacts', [])
        password = data.pop('password')
        data.pop('password2')
        data.pop('recaptcha')
            
        user = User.objects.create(**data)
        user.is_active = True
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact)
            except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                break

        user.save()

    def login_user(self, email=None):
        """
        Установка токена авторизации
        """
        if is_dict(email):
            email = email.get('email')
        if not email:
            self.clear_credentials()
            return
        user = User.objects.get(email=email)
        token = Token.objects.get_or_create(user_id=user.id)[0].key
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def clear_credentials(self):
        """
        Очистка токена авторизации
        """
        self.client.credentials(HTTP_AUTHORIZATION='')

    def load_shop_data(self):
        with open(os.path.join(settings.MEDIA_ROOT, 'tests/shop1.json'), 'rb') as fp:
            response = self.client.post(reverse('api:partner-update'),
                                        data=encode_multipart(BOUNDARY, {'file': fp}), 
                                        content_type=MULTIPART_CONTENT)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def setUp(self):
        """
        Предустановки
        """
        # self.job_title = "test job"
        # self.job_description = "lorem ipsum dolor sit amet"
        self.create_user(self.buyer1_data)
        self.create_user(self.buyer2_data)
        self.create_user(self.shop_owner1_data)
        self.create_user(self.shop_owner2_data)
        self.login_user(self.shop_owner1_data)
        self.load_shop_data()
        self.clear_credentials()

    def test_get_shop_state(self):
        """
        Тест получения статуса магазина
        """
        self.login_user(self.shop_owner1_data)
        response = self.client.get(reverse('api:partner-state'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('data', response.data)
        self.assertTrue(is_list(response.data['data']))
        for item in response.data['data']:
            self.assertIn('url', item)
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('state', item)
        self.assertEqual(len(response.data['data']), 1)

    def test_get_shop_state_noshops(self):
        """
        Тест получения статуса магазинов пользователем, у которого нет
        зарегистрированных магазинов
        """
        self.login_user(self.shop_owner2_data)
        response = self.client.get(reverse('api:partner-state'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('data', response.data)
        self.assertTrue(is_list(response.data['data']))
        self.assertEqual(len(response.data['data']), 0)

    def test_put_shop_state(self):
        """
        Тест установки статуса магазина
        """
        self.login_user(self.shop_owner1_data)

        response = self.client.put(reverse('api:partner-state'), data={'state': 'true'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('state', response.data)
        self.assertTrue(response.data['state'])
        self.assertIn('application/json', response.accepted_media_type)
        shops = User.objects.get(email=self.shop_owner1_data['email']).shops.all()
        for shop in shops:
            self.assertTrue(shop.state)

        response = self.client.put(reverse('api:partner-state'), data={'state': 'false'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('state', response.data)
        self.assertFalse(response.data['state'])
        self.assertIn('application/json', response.accepted_media_type)
        shops = User.objects.get(email=self.shop_owner1_data['email']).shops.all()
        for shop in shops:
            self.assertFalse(shop.state)

    
    def test_get_shop_state_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может полуать статусы магазина
        """
        response = self.client.get(reverse('api:partner-state'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('data', response.data)

    def test_get_shop_state_nonshop_rejected(self):
        """
        Тест, что пользователь-покупатель не может получать статус магазина
        """
        self.login_user(self.buyer1_data)

        response = self.client.get(reverse('api:partner-state'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('data', response.data)

    def test_put_shop_state_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может изменять статусы магазинов
        """
        response = self.client.put(reverse('api:partner-state'), format='json', data={'state': 'false'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('data', response.data)
        self.assertNotIn('state', response.data)

    def test_put_shop_state_nonshop_rejected(self):
        """
        Тест, что пользователь-покупатель не может изменять статусы магазинов
        """
        self.login_user(self.buyer1_data)

        response = self.client.put(reverse('api:partner-state'), format='json', data={'state': 'false'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('data', response.data)
        self.assertNotIn('state', response.data)
        
    def test_get_contacts_shop_user(self):
        """
        Тест получения контактов пользователем-поставщиком
        """
        self.login_user(self.shop_owner1_data)
        response = self.client.get(reverse('api:contact-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertTrue(is_list(response.data['results']))
        for item in response.data['results']:
            self.assertIn('url', item)
            self.assertIn('person', item)
            self.assertIn('phone', item)
            self.assertIn('city', item)
            self.assertIn('street', item)
            self.assertIn('house', item)
            self.assertIn('structure', item)
            self.assertIn('building', item)
            self.assertIn('apartment', item)
            self.assertIn('user', item)
        self.assertEqual(len(response.data['results']), len(self.shop_owner1_data['contacts']))

    def test_get_contacts_buyer(self):
        """
        Тест получения контактов пользователем-покупателем
        """
        self.login_user(self.buyer1_data)
        response = self.client.get(reverse('api:contact-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertTrue(is_list(response.data['results']))
        for item in response.data['results']:
            self.assertIn('url', item)
            self.assertIn('person', item)
            self.assertIn('phone', item)
            self.assertIn('city', item)
            self.assertIn('street', item)
            self.assertIn('house', item)
            self.assertIn('structure', item)
            self.assertIn('building', item)
            self.assertIn('apartment', item)
            self.assertIn('user', item)
        self.assertEqual(len(response.data['results']), len(self.buyer1_data['contacts']))

    def test_get_contacts_anonymous_rejected(self):
        """
        Тест, то анонимный пользователь не может прочитать контакты
        """
        response = self.client.get(reverse('api:contact-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

    def test_retrieve_contact_shop_user(self):
        """
        Тест чтения конретного контакта поставщиком
        """
        self.login_user(self.shop_owner1_data)
        id = User.objects.get(email=self.shop_owner1_data['email']).contacts.first().id
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('url', response.data)
        self.assertIn('person', response.data)
        self.assertIn('phone', response.data)
        self.assertIn('city', response.data)
        self.assertIn('street', response.data)
        self.assertIn('house', response.data)
        self.assertIn('structure', response.data)
        self.assertIn('building', response.data)
        self.assertIn('apartment', response.data)
        self.assertIn('user', response.data)

    def test_retrieve_contact_buyer(self):
        """
        Тест чтения конкретного контакта покупателем
        """
        self.login_user(self.buyer1_data)
        id = User.objects.get(email=self.buyer1_data['email']).contacts.first().id
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('url', response.data)
        self.assertIn('person', response.data)
        self.assertIn('phone', response.data)
        self.assertIn('city', response.data)
        self.assertIn('street', response.data)
        self.assertIn('house', response.data)
        self.assertIn('structure', response.data)
        self.assertIn('building', response.data)
        self.assertIn('apartment', response.data)
        self.assertIn('user', response.data)

    def test_retrieve_contact_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может прочитать конкретный контакт
        """
        id = User.objects.get(email=self.buyer1_data['email']).contacts.first().id
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

    def test_retrieve_contact_another_user_rejected(self):
        """
        Тест, что нельзя прочитать контакт другого пользователя
        """
        self.login_user(self.shop_owner1_data)
        id = User.objects.get(email=self.buyer1_data['email']).contacts.first().id
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

    def test_retrieve_nonexisting_contact_rejected(self):
        """
        Тест попытки чтения не существующего контакта
        """
        self.login_user(self.shop_owner1_data)
        id = 500000
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

        id = 'ggg'
        response = self.client.get(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)

    def test_delete_contact_buyer(self):
        """
        Тест удаления контакта покупателем
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.delete(reverse('api:contact-detail', kwargs={'pk': id}), format='json')
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertEqual(count + 1, old_count)

    def test_delete_contact_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может удалить контакт
        """
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = User.objects.get(email=self.buyer1_data['email']).contacts.first().id
        count = contacts.count()
        response = self.client.delete(reverse('api:contact-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertEqual(count, old_count)

    def test_edit_contact_buyer(self):
        """
        Тест, что покупатель может редактировать контакт
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.put(reverse('api:contact-detail', kwargs={'pk': id}), format='json',
                                   data={'phone': '+79168248482', 'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        # self.assertIn('Status', response.data)
        # self.assertEqual(response.data['Status'], True)

        self.assertEqual(contacts.first().phone, '+79168248482')
        self.assertEqual(contacts.first().person, 'NewPerson')
        self.assertEqual(contacts.first().city, '')
        self.assertEqual(count, old_count)

        self.assertEqual(response.data['phone'], '+79168248482')
        self.assertEqual(response.data['person'], 'NewPerson')
        self.assertEqual(response.data['city'], '')

    def test_edit_contact_buyer_not_all_fields(self):
        """
        Тест попытки редактирования контакта покупателем, если не заполнены необходимые поля
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.put(reverse('api:contact-detail', kwargs={'pk': id}), format='json',
                                   data={'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

        self.assertEqual(contacts.first().phone, self.buyer1_data['contacts'][0]['phone'])
        self.assertEqual(contacts.first().person, self.buyer1_data['contacts'][0]['person'])
        self.assertEqual(contacts.first().city, self.buyer1_data['contacts'][0]['city'])
        self.assertEqual(count, old_count)

        self.assertNotIn('phone', response.data)
        self.assertNotIn('person', response.data)
        self.assertNotIn('city', response.data)

    def test_edit_contact_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может редактировать контакт
        """
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.put(reverse('api:contact-detail', kwargs={'pk': id}), format='json',
                                   data={'phone': '+79168248482', 'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

        self.assertEqual(contacts.first().phone, self.buyer1_data['contacts'][0]['phone'])
        self.assertEqual(contacts.first().person, self.buyer1_data['contacts'][0]['person'])
        self.assertEqual(contacts.first().city, self.buyer1_data['contacts'][0]['city'])
        self.assertEqual(count, old_count)

        self.assertNotIn('phone', response.data)
        self.assertNotIn('person', response.data)
        self.assertNotIn('city', response.data)

    def test_partial_edit_contact_buyer(self):
        """
        Тест попытки частичного редактирования контакта
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        id = contacts.first().id
        response = self.client.patch(reverse('api:contact-detail', kwargs={'pk': id}), format='json',
                                     data={'phone': '+79168248482'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        # self.assertIn('Status', response.data)
        # self.assertEqual(response.data['Status'], True)

        self.assertEqual(contacts.first().phone, '+79168248482')
        self.assertEqual(contacts.first().person, self.buyer1_data['contacts'][0]['person'])
        self.assertEqual(contacts.first().city, self.buyer1_data['contacts'][0]['city'])
        self.assertEqual(count, old_count)

        self.assertEqual(response.data['phone'], '+79168248482')
        self.assertEqual(response.data['person'], self.buyer1_data['contacts'][0]['person'])
        self.assertEqual(response.data['city'], self.buyer1_data['contacts'][0]['city'])


    def test_create_contact_buyer(self):
        """
        Тест создания контакта покупателем
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        response = self.client.post(reverse('api:contact-list'), format='json',
                                    data={'phone': '+79168248482', 'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)

        self.assertEqual(contacts.last().phone, '+79168248482')
        self.assertEqual(contacts.last().person, 'NewPerson')
        self.assertEqual(contacts.last().city, '')
        self.assertEqual(count, old_count + 1)

    def test_create_contact_buyer_not_all_fields(self):
        """
        Тест создания контакта покупателем, не все необходимые поля заполнены
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        response = self.client.post(reverse('api:contact-list'), format='json',
                                    data={'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_create_contact_anonymous_rejected(self):
        """
        Тест, что анонимный пользователь не может создать контакт
        """
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        response = self.client.post(reverse('api:contact-list'), format='json',
                                    data={'phone': '+79168248482', 'person': 'NewPerson'})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_bulk_delete_contact_buyer(self):
        """
        Тест группового удаления контактов покупателем
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = ','.join([ str(contacts.first().id), str(contacts.last().id) ])
        response = self.client.delete(reverse('api:contact-bulkdelete'), format='json',
                                    data={'items': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(count, old_count - 2)

    def test_bulk_delete_post_contact_buyer(self):
        """
        Тест группового удаления контактов покупателем методом POST
        (метод POST дублирует DELETE, чтобы запросы можно было выполнять в web api,
        т.к. web api не создает формы для DELETE)
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = ','.join([ str(contacts.first().id), str(contacts.last().id) ])
        response = self.client.post(reverse('api:contact-bulkdelete'), format='json',
                                    data={'items': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(count, old_count - 2)

    def test_bulk_delete_contact_buyer_no_items(self):
        """
        Тест группового удаления контактов, если не задано необходимое поле items
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = ','.join([ str(contacts.first().id), str(contacts.last().id) ])
        response = self.client.delete(reverse('api:contact-bulkdelete'), format='json',
                                      data={'some': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_bulk_delete_contact_buyer_non_str_items(self):
        """
        Тест попытки группового удаления контактов пользовтаелем, если items заданы не как строка
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = [ str(contacts.first().id), str(contacts.last().id) ]
        response = self.client.delete(reverse('api:contact-bulkdelete'), format='json',
                                      data={'items': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_bulk_delete_contact_buyer_non_positive_items(self):
        """
        Тест попытки группового удаления контактов покупателя при наличии отрицательных значений в перечне items
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = ','.join([ str(contacts.first().id), str(contacts.last().id), str(-1) ])
        response = self.client.delete(reverse('api:contact-bulkdelete'), format='json',
                                      data={'items': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_bulk_delete_contact_buyer_non_existing_items(self):
        """
        Тест группового удаления контактов с несуществующими контактами в перечне
        """
        self.login_user(self.buyer1_data)
        contacts = User.objects.get(email=self.buyer1_data['email']).contacts
        old_count = contacts.count()
        items = ','.join([ str(contacts.first().id), str(contacts.last().id), str(50000) ])
        response = self.client.delete(reverse('api:contact-bulkdelete'), format='json',
                                      data={'items': items})
        count = contacts.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)


    def test_get_product_info(self, query=''):
        """
        Тест получения списка продуктов
        """
        response = self.client.get(reverse('api:productinfo-list') + query, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertTrue(is_list(response.data['results']))
        for item in response.data['results']:
            self.assertIn('url', item)
            self.assertIn('id', item)
            self.assertIn('product', item)
            self.assertIn('shop', item)
            self.assertIn('quantity', item)
            self.assertIn('price', item)
            self.assertIn('price_rrc', item)
            self.assertIn('product_parameters', item)

            product = item['product']
            self.assertTrue(is_dict(product))
            self.assertIn('name', product)
            self.assertIn('category', product)

            category = product['category']
            self.assertTrue(is_dict(category))
            self.assertIn('url', category)
            self.assertIn('id', category)
            self.assertIn('name', category)

            shop = item['shop']
            self.assertTrue(is_dict(shop))
            self.assertIn('url', shop)
            self.assertIn('name', shop)

            self.assertTrue(is_list(item['product_parameters']))
            for entry in item['product_parameters']:
                self.assertIn('parameter', entry)
                self.assertIn('value', entry)

    def test_retrieve_product_info(self):
        """
        Тест получения информации по продукту
        """
        id = ProductInfo.objects.first().id
        response = self.client.get(reverse('api:productinfo-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)

        self.assertIn('url', response.data)
        self.assertIn('id', response.data)
        self.assertIn('product', response.data)
        self.assertIn('shop', response.data)
        self.assertIn('quantity', response.data)
        self.assertIn('price', response.data)
        self.assertIn('price_rrc', response.data)
        self.assertIn('product_parameters', response.data)

        product = response.data['product']
        self.assertTrue(is_dict(product))
        self.assertIn('name', product)
        self.assertIn('category', product)

        category = product['category']
        self.assertTrue(is_dict(category))
        self.assertIn('url', category)
        self.assertIn('id', category)
        self.assertIn('name', category)

        shop = response.data['shop']
        self.assertTrue(is_dict(shop))
        self.assertIn('url', shop)
        self.assertIn('name', shop)

        self.assertTrue(is_list(response.data['product_parameters']))
        for entry in response.data['product_parameters']:
            self.assertIn('parameter', entry)
            self.assertIn('value', entry)
        
    def test_get_product_info_query_shop_id(self, query=''):
        """
        Тест получения списка продуктов с фильтрацией по магазину
        """
        shop_id = Shop.objects.first().id
        query = f'?shop_id={shop_id}'
        self.test_get_product_info(query)

    def test_get_product_info_query_category_id(self, query=''):
        """
        Тест получения списка продуктов с фильтрацией по категории
        """
        category_id = Category.objects.first().id
        query = f'?category_id={category_id}'
        self.test_get_product_info(query)

    def test_get_product_info_double_query(self, query=''):
        """
        Тест получения списка продуктов с фильтрацией по магазину и категории
        """
        shop_id = Shop.objects.first().id
        category_id = Category.objects.first().id
        query = f'?category_id={category_id}&shop_id={shop_id}'
        self.test_get_product_info(query)


    def test_add_item_to_basket(self):
        """
        Тест добавления товара в корзину
        """
        self.login_user(self.buyer1_data)
        user = User.objects.get(email=self.buyer1_data['email'])
        id = ProductInfo.objects.first().id
        quantity = 5
        response = self.client.put(reverse('api:basket-add_goods'), format='json',
                                   data={'product_info': id, 'quantity': quantity})

        self.assertTrue(Order.objects.filter(user_id=user.id, state='basket').exists())
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(ordered_items.count(), 1)
        self.assertEqual(ordered_items.first().product_info_id, id)
        self.assertEqual(ordered_items.first().quantity, quantity)

    def test_add_same_item_to_basket(self):
        """
        Тест повторного добавления товара в корзину
        """
        self.login_user(self.buyer1_data)
        user = User.objects.get(email=self.buyer1_data['email'])
        id = ProductInfo.objects.first().id
        quantity = 5

        self.client.put(reverse('api:basket-add_goods'), format='json',
                        data={'product_info': id, 'quantity': quantity})

        response = self.client.put(reverse('api:basket-add_goods'), format='json',
                                   data={'product_info': id, 'quantity': quantity})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

        self.assertTrue(Order.objects.filter(user_id=user.id, state='basket').exists())
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        self.assertEqual(ordered_items.count(), 1)

    def test_add_goods_to_basket(self):
        """
        Тест добавления списка товаров в корзину
        """
        self.login_user(self.buyer1_data)
        user = User.objects.get(email=self.buyer1_data['email'])
        id1=ProductInfo.objects.first().id
        id2=ProductInfo.objects.last().id
        ids = f'[ {{ "product_info": {id1}, "quantity": 5 }}, {{ "product_info": {id2}, "quantity": 5 }} ]'
        response = self.client.put(reverse('api:basket-add_goods'), format='json',
                                   data={'items': ids})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)

        self.assertTrue(Order.objects.filter(user_id=user.id, state='basket').exists())
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        self.assertEqual(ordered_items.count(), 2)

    def test_add_goods_to_basket_wrong_format(self):
        """
        Тест попытки добавления в корзину неправильно отформатированного списка товаров
        """
        self.login_user(self.buyer1_data)
        user = User.objects.get(email=self.buyer1_data['email'])
        ids = 'gggg'
        response = self.client.put(reverse('api:basket-add_goods'), format='json',
                                   data={'items': ids})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

        self.assertFalse(Order.objects.filter(user_id=user.id, state='basket').exists())

    def test_list_basket(self):
        """
        Тест просмотра корзины
        """
        self.login_user(self.buyer1_data)
        self.test_add_item_to_basket()
        response = self.client.get(reverse('api:basket-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('data', response.data)
        self.assertTrue(is_list(response.data['data']))
        for item in response.data['data']:
            self.assertIn('ordered_items', item)
            self.assertIn('total_sum', item)
            total = float(item['total_sum'])
            sum = 0
            self.assertTrue(is_list(item['ordered_items']))
            for entry in item['ordered_items']:
                self.assertIn('id', entry)
                self.assertIn('product_info', entry)
                self.assertIn('quantity', entry)
                quantity = int(entry['quantity'])
                product_info = entry['product_info']
                self.assertTrue(is_dict(product_info))
                self.assertIn('id', product_info)
                self.assertIn('url', product_info)
                self.assertIn('product', product_info)
                self.assertIn('shop', product_info)
                self.assertIn('price', product_info)
                price = float(product_info['price'])
                sum += price * quantity
                self.assertIn('price_rrc', product_info)
                shop = product_info['shop']
                self.assertTrue(is_dict(shop))
                self.assertIn('id', shop)
                self.assertIn('url', shop)
                self.assertIn('name', shop)
            self.assertEqual(total, sum)

        
    def test_basket_delete_goods(self):
        """
        Тест группового удаления товаров из корзины
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = ','.join([ str(ordered_items.first().id), str(ordered_items.last().id) ])
        response = self.client.delete(reverse('api:basket-delete_goods'), format='json',
                                      data={'items': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(count, old_count - 2)


    def test_basket_delete_goods_post(self):
        """
        Тест группового удаления товаров из корзины
        (метод POST дублирует DELETE, чтобы запросы можно было выполнять в web api,
        т.к. web api не создает формы для DELETE)
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = ','.join([ str(ordered_items.first().id), str(ordered_items.last().id) ])
        response = self.client.post(reverse('api:basket-delete_goods'), format='json',
                                    data={'items': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertNotIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(count, old_count - 2)

    def test_basket_delete_goods_no_items(self):
        """
        Тест попытки группового удаления товаров из корзины, если не задан список товаров
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = ','.join([ str(ordered_items.first().id), str(ordered_items.last().id) ])
        response = self.client.delete(reverse('api:basket-delete_goods'), format='json',
                                      data={'some': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_basket_delete_goods_non_str_items(self):
        """
        Тест попытки группового удаления товаров из корзины, если список товаров не строка
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = [ str(ordered_items.first().id), str(ordered_items.last().id) ]
        response = self.client.delete(reverse('api:basket-delete_goods'), format='json',
                                      data={'items': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)
    
    def test_basket_delete_goods_non_positive_items(self):
        """
        Тест попытки группового удаления товаров из корзины, если заданы товары с отрицательными индексами
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = ','.join([ str(ordered_items.first().id), str(ordered_items.last().id), str(-1) ])
        response = self.client.delete(reverse('api:basket-delete_goods'), format='json',
                                      data={'items': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_basket_delete_goods_non_existing_items(self):
        """
        Тест попытки группового удаления товаров из корзины, если не задан список товаров с несуществующими индексами
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        ordered_items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        old_count = ordered_items.count()
        items = ','.join([ str(ordered_items.first().id), str(ordered_items.last().id), str(50000) ])
        response = self.client.delete(reverse('api:basket-delete_goods'), format='json',
                                      data={'items': items})
        count = ordered_items.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Errors', response.data)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertEqual(count, old_count)

    def test_set_quantity_to_basket(self):
        """
        Тест установки количества товара 
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        id = items.first().id
        quantity = 25
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'id': id, 'quantity': quantity})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(items.get(id=id).quantity, quantity)

    def test_bulk_set_quantity_to_basket(self):
        """
        Тест групповой установки количества товаров в корзине 
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        items = Order.objects.get(user_id=user.id, state='basket').ordered_items
        id1=items.first().id
        id2=items.last().id
        quantity = 24
        values = f'[ {{ "id": {id1}, "quantity": {quantity} }}, {{ "id": {id2}, "quantity": {quantity} }} ]'
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertEqual(items.get(id=id1).quantity, quantity)
        self.assertEqual(items.get(id=id2).quantity, quantity)

    def test_set_quantity_to_basket_wrong_format(self):
        """
        Тест попытки установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'quantity': 5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_set_quantity_to_basket_wrong_format2(self):
        """
        Тест попытки установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'id': 'id', 'quantity': 5})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_bulk_set_quantity_to_basket_wrong_format(self):
        """
        Тест попытки групповой установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        values = '{ "id": 1, "quantity": 12 }'
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_bulk_set_quantity_to_basket_wrong_format2(self):
        """
        Тест попытки групповой установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        values = ''
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_bulk_set_quantity_to_basket_wrong_format3(self):
        """
        Тест попытки групповой установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        values = '[ { "quantity": 12 } ]'
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_bulk_set_quantity_to_basket_wrong_format4(self):
        """
        Тест попытки групповой установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        values = '[ { "id": "ggg", "quantity": 12 } ]'
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_bulk_set_quantity_to_basket_wrong_format5(self):
        """
        Тест попытки групповой установки количества товаров в корзине, неверный формат исходных данных
        """
        self.test_add_goods_to_basket()
        values = '[ { '
        response = self.client.put(reverse('api:basket-set_quantity'), format='json',
                                   data={'items': values})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_make_order(self):
        """
        Тест создания заказа
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        contact =user.contacts.first()

        response = self.client.post(reverse('api:order-list'), format='json',
                                    data={'contact': contact.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertTrue(user.orders.filter(state='new').exists())

    def test_try_make_order_no_items(self):
        """
        Тест попытки создания заказа с пустым списком товаров в корзине
        """
        self.login_user(self.buyer1_data)
        user = User.objects.get(email=self.buyer1_data['email'])
        contact =user.contacts.first()

        response = self.client.post(reverse('api:order-list'), format='json',
                                    data={'contact': contact.id})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertFalse(user.orders.filter(state='new').exists())

    def test_try_make_order_wrong_contact(self):
        """
        Тест попытки создания заказа с неправильным указаниаем контакта
        """
        self.test_add_goods_to_basket()
        user = User.objects.get(email=self.buyer1_data['email'])
        contact_id =5000

        response = self.client.post(reverse('api:order-list'), format='json',
                                    data={'contact': contact_id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contact', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        self.assertFalse(user.orders.filter(state='new').exists())

    def test_try_make_order_anonymous(self):
        """
        Тест попытки создания заказа анонимным пользователем
        """
        response = self.client.post(reverse('api:order-list'), format='json',
                                    data={'contact': 500})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_try_make_order_nodata(self):
        """
        Тест попытки создания заказа, исходные данные не указаны
        """
        self.login_user(self.buyer1_data)
        response = self.client.post(reverse('api:order-list'), format='json',
                                    data={})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contact', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_list_orders(self):
        """
        Тест получения списка заказов покупателем
        """
        self.test_make_order()
        response = self.client.get(reverse('api:order-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertTrue(is_list(response.data['results']))
        for item in response.data['results']:
            self.assertIn('url', item)
            self.assertIn('id', item)
            self.assertIn('ordered_items', item)
            self.assertIn('state', item)
            self.assertIn('dt', item)
            self.assertIn('total_sum', item)
            self.assertIn('contact', item)

    def test_list_orders_anonymous(self):
        """
        Тест попытки получения списка заказов как покупателя анонимным пользователем
        """
        response = self.client.get(reverse('api:order-list'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_retrieve_orders(self):
        """
        Тест чтения информации по заказу
        """
        self.test_make_order()
        id = User.objects.get(email=self.buyer1_data['email']).orders.first().id
        response = self.client.get(reverse('api:order-detail', kwargs={'pk': id}), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('url', response.data)
        self.assertIn('id', response.data)
        self.assertIn('ordered_items', response.data)
        self.assertIn('state', response.data)
        self.assertIn('dt', response.data)
        self.assertIn('total_sum', response.data)
        self.assertIn('contact', response.data)

    def test_retrieve_orders_anonymous(self):
        """
        Тест попытки чтения информации по заказу анонимным пользователем
        """
        response = self.client.get(reverse('api:order-detail', kwargs={'pk': 1}), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)
        
    def test_list_partner_orders(self):
        """
        Тест получения списка заказов поставщиком
        """
        self.test_make_order()
        self.login_user(self.shop_owner1_data)
        response = self.client.get(reverse('api:partner-orders'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], True)
        self.assertIn('data', response.data)
        self.assertTrue(is_list(response.data['data']))
        for item in response.data['data']:
            self.assertIn('url', item)
            self.assertIn('id', item)
            self.assertIn('ordered_items', item)
            self.assertIn('state', item)
            self.assertIn('dt', item)
            self.assertIn('total_sum', item)
            self.assertIn('contact', item)

    def test_list_partner_orders_anonymous(self):
        """
        Тест попытки получения списка заказов как поставщиком анонимным пользователем
        """
        response = self.client.get(reverse('api:partner-orders'), format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Errors', response.data)
        self.assertIn('application/json', response.accepted_media_type)
        self.assertIn('Status', response.data)
        self.assertEqual(response.data['Status'], False)

    def test_schema(self):
        """
        Тест чтения OpenAPI схемы
        """
        self.login_user(self.shop_owner1_data)
        response = self.client.get(reverse('api:openapi-schema'), format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('application/vnd.oai.openapi', response.accepted_media_type)



