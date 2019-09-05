from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile as FileClass
from django.core.validators import URLValidator
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework_xml.parsers import XMLParser
from requests import get, RequestException
import os
from ujson import loads as load_json
from yaml import load as load_yaml, Loader, YAMLError

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from .response import ResponseCreated, ResponseBadRequest, ResponseForbidden, ResponseNotFound
from .utils import to_decimal, to_positive_int, is_dict, is_list


def load_xml(stream):
    """
    Parses the incoming bytestream as XML and returns the resulting data.
    """

    return XMLParser().parse(ContentFile(stream))


def load_partner_info(url=None, file_obj=None, user_id=0):
    """
    Обновление прайса от поставщика
    """
    if not url and not (file_obj and isinstance(file_obj, FileClass)):
        return ResponseBadRequest('Не указаны все необходимые аргументы. Нужно указать url или загрузить файл')
    if file_obj:
        stream = file_obj.read()
        _, extension = os.path.splitext(file_obj.name)
        mime = ''
    else:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return ResponseBadRequest(e)

        try:
            response = get(url)
        except RequestException as e:
            return ResponseNotFound(e)
        _, extension = os.path.splitext(url)
        stream = response.content
        mime = response.headers.get('content-type')
    try:
        if mime in ('application/x-yaml', 'text/yaml'):
            data = load_yaml(stream, Loader=Loader)
        elif mime in ('application/json', 'text/json'):
            data = load_json(stream)
        elif mime in ('application/xml', 'text/xml'):
            data = load_xml(stream)
        elif extension == '.yaml':
            data = load_yaml(stream, Loader=Loader)
        elif extension == '.json':
            data = load_json(stream)
        elif extension == '.xml':
            data = load_xml(stream)
        else:
            return ResponseBadRequest('Не опознан формат файла {}', url)
    except (ParseError, YAMLError, ValueError, TypeError) as e:
        return ResponseBadRequest('Некорректный формат файла: {}', e)

    # Check format:
    if not is_dict(data):
        return ResponseBadRequest('Некорректный формат файла: исходные данные должны представлять собой словарь')
    version = data.get('version')
    if not version or version != 'v1.0':
        return ResponseBadRequest('Некорректный формат файла: не поддерживается версия {}', version)
    if not data.get('shop'):
        return ResponseBadRequest('Некорректный формат файла: не задано/некорректное название магазина')
    categories = data.get('categories', [])
    if not is_list(categories):
        return ResponseBadRequest('Некорректный формат файла: категории должны быть заданы в списке')
    for category in categories:
        if not is_dict(category):
            return ResponseBadRequest('Некорректный формат файла: категории должны быть описаны как словарь') 
        if not category.get('name'):
            return ResponseBadRequest('Некорректный формат файла: не задано/некорректное название категории')
    goods = data.get('goods', [])
    if not is_list(goods):
        return ResponseBadRequest('Некорректный формат файла: товары должны быть заданы в списке')
    names = set()
    for item in goods:
        if not is_dict(item):
            return ResponseBadRequest('Некорректный формат файла: товары должны быть описаны как словарь') 
        name = item.get('name')
        category = item.get('category')
        price = to_decimal(item.get('price'))
        price_rrc = to_decimal(item.get('price_rrc'))
        quantity = to_positive_int(item.get('quantity'))
        if not name or not category or None in (price, price_rrc, quantity):
            return ResponseBadRequest('Некорректный формат файла: некорректно указана информация по продукту {}', name)
        if name in names:
            return ResponseBadRequest('Некорректный формат файла: продукты с одинаковым именем')
        names.add(name)
        parameters = item.get('parameters')
        if parameters is not None:
            if not is_list(parameters):
                return ResponseBadRequest('Некорректный формат файла: параметры для продукта {} должны быть заданы как массив полей name и value', name)
            parameter_names = set()
            for entry in parameters:
                if not is_dict(entry):
                    return ResponseBadRequest('Некорректный формат файла: параметр для продукта должен быть описан как словарь (продукт {})', name)
                par_name = entry.get('name')
                if not par_name or entry.get('value') is None:
                    return ResponseBadRequest('Некорректный формат файла: параметры для продукта {} должны иметь не пустые значения name и value', name)
                if par_name in parameter_names:
                    return ResponseBadRequest('Некорректный формат файла: параметры с одинаковым именем у продукта {}', name)
                parameter_names.add(par_name)
    # Actions:
    shop, _ = Shop.objects.get_or_create(name=data['shop'], defaults=dict(user_id=user_id))
    if shop.user_id != user_id:
        return ResponseForbidden('Магазин не принадлежит пользователю')
    for category in data.get('categories', []):
        category_object, _ = Category.objects.get_or_create(name=category['name'])
        category_object.shops.add(shop.id)
        category_object.save()
    ProductInfo.objects.filter(shop_id=shop.id).delete()
    for item in data.get('goods', []):           
        category_object, _ = Category.objects.get_or_create(name=item['category'])
        product, _ = Product.objects.get_or_create(name=item['name'], category_id=category_object.id)

        product_info = ProductInfo.objects.create(product_id=product.id,
                                                  external_id=item.get('id'),
                                                  price=item['price'],
                                                  price_rrc=item['price_rrc'],
                                                  quantity=item['quantity'],
                                                  shop_id=shop.id)
        for entry in item.get('parameters', []):
            parameter_object, _ = Parameter.objects.get_or_create(name=entry.get('name'))
            ProductParameter.objects.create(product_info_id=product_info.id,
                                            parameter_id=parameter_object.id,
                                            value=entry.get('value'))
    return ResponseCreated()
  