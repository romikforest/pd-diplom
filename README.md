# pd-diplom-webshop

Коптев Р.В.
Дипломная работа к профессии Python-разработчик (API Сервис заказа товаров для розничных сетей)

## Установка

Выполните преднастройку git:

    git config --global user.name "YOUR_USERNAME"
    git config --global user.email "your_email_address@example.com"

Создайте каталог для клонирования дипломного проекта и клонируйте проект:

    mkdir ~/kr_diplom
    cd kr_diplom
    git clone https://github.com/romikforest/pd-diplom.git

Создайте python окружение для проекта средствами, которые вы используете,
и активируйте его, например:

    conda create -n rk-diplom
    conda install -n rk-diplom m2-bash
    conda install -n rk-diplom pip
    source activate rk-diplom

Перейдите в склонированный проект, установите зависимости,
подготовьте базу данных и создайте административный аккаунт:

    cd pd_diplom
    pip install -r requirements.txt
    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser

## Установка и запуск redis server и celary server

Для полноценной работы приложения вам потребуется использовать
celary в качестве очереди задач и redis-server
в качестве брокера сообщений.

Установите redis-server следуя инструкциям по ссылке:

    https://redis.io/download

Для установки redis-server на windows его можно скачать по ссылке:

    https://github.com/MicrosoftArchive/redis/releases

После чего распакуйте архив, перейдите в созданный каталог и запустите файл
redis-server.exe

celary установлена после установки зависимостей проекта. Просто
запустите ее в новом окне эмулятора терминала с активированным окружением
Python в каталоге проекта:

celery worker -A orders --loglevel=info --concurrency=4 --pool=gevent

Используйте опцию --pool=gevent на windows

## Запуск тестового сервера

Вы можете тестировать приложение с помощью тестового сервера:

    python manage.py runserver

## Запуск тестов

Вы можете запустить тесты как обычно:

    python manage.py test

При этом оценка покрытия с помощью coverage уже интегрирована в проект и
сама система coverage установлена с остальными зависимостями

*Внимание! Перед запуском тестов обязательно запустите redis-server*

Вы можете использовать систему coverage как обычно. Например, сгенерировать
html документацию, просматривать ее в браузере, видеть какие строки
отработали в тестах:

    coverage html

Подробнее о командах coverage можно ознакомится в документации:

    https://coverage.readthedocs.io/en/v4.5.x/

## web api, OpenAPI схема, документация

После запуска тестового сервера web api доступно по ссылке:

    http://127.0.0.1:8000/api/v1/

Редирект на нее происходит при заходе на главную страницу:

    http://127.0.0.1:8000/

Доступны также автоматические swagger и redoc документация:

    http://127.0.0.1:8000/api/v1/swagger-ui
    http://127.0.0.1:8000/api/v1/redoc#operation/ListUsers

API также опубликовано на сервере POSTMAN:

    https://documenter.getpostman.com/view/5388014/SVmwvdBw
