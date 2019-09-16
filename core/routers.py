from collections import OrderedDict
from django.conf.urls import url

from rest_framework import routers

# ViewSet роутеры:

class CustomDefaultRouter(routers.DefaultRouter):
    """
    Миксин для DefaultRouter
    Роутер генерирует пути для конечного слеша и без него
    Он также старается добавить простые пути в api root view, не только list
    С помощью свойств root_view_pre_items и root_view_post_items
    можно добавить дополнительные поля в api root view
    соответсвенно до и после зарегистрированных роутов
    (ключ - отображаемый ключ, значение - имя в urlpatterns) 
    """
    root_view_pre_items = OrderedDict()
    root_view_post_items = OrderedDict()

    def get_urls(self):
        urls = super(CustomDefaultRouter, self).get_urls()
        for i in range(len(urls)):
            regex = str(urls[i].pattern)
            if regex[-2:] == '/$':
                regex = regex[:-2] + '/?$'
            urls[i] = url(regex=regex, view=urls[i].callback, name=urls[i].name)
        return urls

    def get_api_root_view(self, api_urls=None):
        """
        Return a basic root view.
        """
        api_root_dict = OrderedDict()
        api_root_dict.update(self.root_view_pre_items)

        viewsets = {}
        prefixes = {}
        for prefix, viewset, basename in self.registry:
            viewsets[viewset] = basename
            prefixes[viewset] = prefix

        for viewset in viewsets:
            routes = self.get_routes(viewset)
            basename = viewsets[viewset]
            prefix = prefixes[viewset]
            for route in routes:
                if not '{lookup}' in route.url:
                    name = route.name.format(basename=basename)
                    url = route.url.format(prefix=prefix, trailing_slash='').replace('^', '').replace('$', '')
                    if len(route.mapping) == 1:
                        method = next(iter(route.mapping)).upper()
                        if method != 'GET':
                            url += f' ({method})'
                    api_root_dict[url] = name

        api_root_dict.update(self.root_view_post_items)

        return self.APIRootView.as_view(api_root_dict=api_root_dict)


class CustomSimpleRouter(routers.SimpleRouter):
    """
    Миксин для SimpleRouter
    Роутер генерирует пути для конечного слеша и без него
    """

    def get_urls(self):
        urls = super(CustomSimpleRouter, self).get_urls()
        for i in range(len(urls)):
            regex = str(urls[i].pattern)
            if regex[-2:] == '/$':
                regex = regex[:-2] + '/?$'
            urls[i] = url(regex=regex, view=urls[i].callback, name=urls[i].name)
        return urls
