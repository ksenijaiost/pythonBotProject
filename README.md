Бот для чата AC. Функционал (в планах).

Главное меню пользователя с кнопками:
1. Гайды - переход в меню гайдов:
   1. Перейти на сайт - кнопка открывает сайт.
   2. Поиск по ключевым словам - человек вводит слово, ему выдаётся подходящий гайд. На данный момент это будет поиск по бд, в будущем подумаем, как улучшить.
2. Конкурсы - переход в меню конкурсов:
   1. Узнать про конкурс - выдаётся актуальная тема, суть, даты + ссылка на анонс и правила. Если актуальной темы нет, то заглушка и ссылка на правила и предыдущие темы. 
   2. Отправить работу - записаться на конкурс как участник и отправить работу (переслать в ADMIN_CHAT_ID, в дальнейшем улучшим). Если запись закрыта, то заглушка. Только для участников чата.
   3. Записаться на судейство - подать заявку, которую мы ещё рассмотрим. Тут будет проверка, что человек не участник. Если запись закрыта - заглушка. Только для участников чата.
3. Сообщение админам - сообщение будет пересылаться в ADMIN_CHAT_ID.
4. Новости в газету - сообщение будет пересылаться в NEWSPAPER_CHAT_ID. Только для участников чата.
5. Репка - пока отключено. Только для участников чата.
6. Наш чат Animal Crossing - ссыль на чат
7. Наш канал - ссыль на канал
8. Чат с темами (оффтоп и разные игры Nintendo) - ссыль на чат
   
Внутри каждого пункта - кнопка "В главное меню".
Внутри каждого подпункта - кнопка "Назад" и "В главное меню".

Главное меню администратора:
1. Конкурс - переход в меню конкурсов:
   1. Сбросить - сбросить счётчики (участники, судейство)
   2. Обновить информацию - добавить информацию о конкурсе (дата, тема, ссылки)
   3. Начать рассылку судьям - выбрать судей и начать рассылку
2. Репка - пока отключено.
3. Добавить гайд - добавить гайд в список.

Для запуска необходим файл .env (пример заполнения - .env.example).
Не забыть - pip install -r /path/to/requirements.txt