# Проект RelateHub

----

Порядок запуска описан для Windows. Команды могут отличаться для вашей системы.

---

Порядок запуска приложения

Сценарий 1: Запуск с Docker Compose (Docker должен быть установлен и 
запушен заранее).
Этот сценарий использует PostgreSQL в контейнере и настройки из .env.
1. Заполните файл .env.docker своими данными и переименуйте в .env 
2. Соберите образы (первый раз): docker-compose build
3. Запустите контейнеры: docker-compose up
4. Выполните миграции (если нужно). В отдельном терминале:
 - docker-compose exec django_app python manage.py migrate
 - docker-compose exec django_app python manage.py createsuperuser

Приложение доступно: http://localhost:8000


Сценарий 2: Запуск без Docker (PostgreSQL необходимо создать и запустить 
заранее).
Этот сценарий использует PostgreSQL и настройки из .env.
1. Заполните файл .env.localhost своими данными и переименуйте в .env
2. Активируйте ваше виртуальное окружение Windows (пример .\venv\Scripts\Activate.ps1)
3. Установите все необходимые библиотеки из requirements.txt: pip install -r requirements.txt
4. Выполните миграции: python manage.py migrate (и создайте администратора, 
   если нужно: python manage.py createsuperuser)
5. Запустите сервер Django: python manage.py runserver

Приложение доступно: http://localhost:8000

---

