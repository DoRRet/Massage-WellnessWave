from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import json
from bot import send_message

from flask import Flask, render_template
from babel.dates import format_datetime
from datetime import datetime

from sqlalchemy.orm import Session

from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from flask import g, session, render_template

example_date = datetime.now()
formatted_date = format_datetime(example_date, "d MMMM yyyy", locale='ru')
print(formatted_date)  # Вывод: 18 августа 2024


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/DICK/Desktop/WellnessWave/WellnessWave/instance/wellnesswave.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Секретный ключ для сессий
db = SQLAlchemy(app)

TASKS_FILE = 'tasks.json'

scheduler = BackgroundScheduler()



# Модели базы данных

class User(db.Model):
    master_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name_master = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sessions = relationship('Sessions', backref='master', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_client = db.Column(db.String(100), nullable=False)
    birthdate = db.Column(db.Date, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    telegram_chat_id = db.Column(db.String(50), nullable=True)
    sessions = relationship('Sessions', backref='client', lazy=True)

class Sessions(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, ForeignKey('client.id'), nullable=False)
    name_client = db.Column(db.String, nullable=False)
    master_id = db.Column(db.Integer, ForeignKey('user.master_id'), nullable=False)
    name_master = db.Column(db.String, nullable=False)
    address_id = db.Column(db.Integer, ForeignKey('addresses.id'), nullable=False)
    procedure_type = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    payment_status = db.Column(db.String, nullable=False)
    details = db.Column(db.String, nullable=True)
    telegram_chat_id = db.Column(db.String, nullable=True)
    address = db.Column(db.String, nullable=False)
    notification_status = db.Column(db.String, nullable=True)  # Добавьте это поле

class Addresses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)

   




def save_tasks_to_file(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f)

def load_tasks_from_file():
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def add_task_to_file(task_id, run_date, session_id, final_message, chat_id):
    tasks = load_tasks_from_file()
    if not any(task['task_id'] == task_id for task in tasks):
        tasks.append({
            'task_id': task_id,
            'run_date': run_date.isoformat(),
            'session_id': session_id,
            'final_message': final_message,
            'chat_id': chat_id
        })
        save_tasks_to_file(tasks)

def remove_task_from_file(task_id):
    tasks = load_tasks_from_file()
    tasks = [task for task in tasks if task['task_id'] != task_id]
    save_tasks_to_file(tasks)

def send_delayed_notification(session_id, final_message, chat_id, job_id):
    with app.app_context():
        send_message(chat_id, final_message)
        session_record = db.session.get(Sessions, session_id)
        if session_record:
            session_record.notification_status = 'Отправлено'
            db.session.commit()
        print(f"Задача {job_id} выполнена.")
        remove_task_from_file(job_id)
        if scheduler.get_job(job_id):
            print(f"Удаление задачи {job_id} из планировщика.")
            scheduler.remove_job(job_id)
        else:
            print(f"Задача {job_id} уже была удалена или не найдена.")



@app.before_request
def load_user():
    # Загрузка информации о текущем пользователе перед каждым запросом
    g.current_user = User.query.get(session.get('user_id'))
    g.user_role = session.get('role')

@app.context_processor
def inject_user_info():
    # Передача информации о пользователе и его роли в шаблоны
    return dict(current_user=g.current_user, user_role=g.user_role)

# Главная страница
@app.route('/')
def index():
    upcoming_birthdays = []
    if g.current_user and g.current_user.role == 'admin':
        today = datetime.today().date()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        # Получаем дни рождения сегодня и завтра
        birthdays_today = Client.query.filter(db.func.strftime('%m-%d', Client.birthdate) == today.strftime('%m-%d')).all()
        birthdays_tomorrow = Client.query.filter(db.func.strftime('%m-%d', Client.birthdate) == tomorrow.strftime('%m-%d')).all()

        # Получаем дни рождения в ближайшие 7 дней, исключая тех, кто уже в списках "Сегодня" и "Завтра"
        birthdays_upcoming = Client.query.filter(
            db.func.strftime('%m-%d', Client.birthdate).between((tomorrow + timedelta(days=1)).strftime('%m-%d'), next_week.strftime('%m-%d'))
        ).all()

        upcoming_birthdays = {
            'today': birthdays_today,
            'tomorrow': birthdays_tomorrow,
            'upcoming': birthdays_upcoming
        }

    return render_template('index.html', upcoming_birthdays=upcoming_birthdays)

@app.template_filter('datetime')
def format_datetime_filter(value, format='d MMMM yyyy', locale='ru'):
    return format_datetime(value, format, locale=locale)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.master_id
            session['role'] = user.role
            return redirect(url_for('index'))  # Перенаправление на главную страницу
        else:
            flash('Неправильное имя пользователя или пароль', 'danger')
    return render_template('login.html')


# Панель управления
@app.route('/dashboard')
def dashboard():
    if g.current_user is None:
        return redirect(url_for('login'))

    users = User.query.count()
    clients = Client.query.count()
    sessions = Sessions.query.count()
    addresses = Addresses.query.count()  # Добавлено для адресов
    return render_template('dashboard.html', users=users, clients=clients, sessions=sessions, addresses=addresses)




# Управление пользователями
@app.route('/users')
def manage_users():
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('users.html', users=users)


@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        name_master = request.form['name_master']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        phone_number = request.form['phone_number']

        new_user = User(username=username, name_master=name_master, password=password, role=role, phone_number=phone_number)
        db.session.add(new_user)
        db.session.commit()
        flash('Мастер успешно добавлен!', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('add_user.html')

# Маршрут для редактирования пользователя
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.username = request.form['username']
        user.name_master = request.form['name_master']
        user.role = request.form['role']
        user.phone_number = request.form['phone_number']

        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])

        db.session.commit()
        flash('Данные мастера успешно обновлены!', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('edit_user.html', user=user)


# Маршрут для удаления пользователя
@app.route('/users/delete/<int:user_id>')
def delete_user(user_id):
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Мастер успешно удален!', 'success')
    return redirect(url_for('manage_users'))


# Управление клиентами
@app.route('/clients')
def manage_clients():
    if g.current_user is None:
        return redirect(url_for('login'))

    clients = Client.query.all()
    return render_template('clients.html', clients=clients)


# Маршрут для добавления клиента
from flask import g

@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    if g.current_user is None:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name_client = request.form['name_client']
        birthdate_str = request.form['birthdate']
        phone_number = request.form['phone_number']
        notes = request.form['notes']

        # Преобразование строки в объект datetime.date
        birthdate = None
        if birthdate_str:
            birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()

        new_client = Client(name_client=name_client, birthdate=birthdate, phone_number=phone_number, notes=notes)
        db.session.add(new_client)
        db.session.commit()
        flash('Клиент успешно добавлен!', 'success')
        return redirect(url_for('manage_clients'))
    
    return render_template('add_client.html')


# Маршрут для редактирования клиента
@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if g.current_user is None:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        client.name_client = request.form['name_client']
        birthdate_str = request.form['birthdate']
        client.phone_number = request.form['phone_number']
        client.notes = request.form['notes']
        
        # Преобразование строки в объект datetime.date
        if birthdate_str:
            client.birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
        else:
            client.birthdate = None

        db.session.commit()
        flash('Данные клиента успешно обновлены!', 'success')
        return redirect(url_for('manage_clients'))
    
    return render_template('edit_client.html', client=client)


# Маршрут для удаления клиента
@app.route('/clients/delete/<int:client_id>')
def delete_client(client_id):
    if g.current_user is None:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Клиент успешно удален!', 'success')
    return redirect(url_for('manage_clients'))





@app.route('/addresses')
def manage_addresses():
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    addresses = Addresses.query.all()
    return render_template('addresses.html', addresses=addresses)


@app.route('/addresses/add', methods=['GET', 'POST'])
def add_address():
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        address = request.form['address']
        new_address = Addresses(address=address)
        db.session.add(new_address)
        db.session.commit()
        flash('Адрес успешно добавлен!', 'success')
        return redirect(url_for('manage_addresses'))
    
    return render_template('add_address.html')


@app.route('/addresses/edit/<int:address_id>', methods=['GET', 'POST'])
def edit_address(address_id):
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))
    
    address = Addresses.query.get_or_404(address_id)

    if request.method == 'POST':
        address.address = request.form['address']
        db.session.commit()
        flash('Адрес успешно обновлен!', 'success')
        return redirect(url_for('manage_addresses'))
    
    return render_template('edit_address.html', address=address)


@app.route('/addresses/delete/<int:address_id>')
def delete_address(address_id):
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))
    
    address = Addresses.query.get_or_404(address_id)
    db.session.delete(address)
    db.session.commit()
    flash('Адрес успешно удален!', 'success')
    return redirect(url_for('manage_addresses'))



@app.route('/sessions')
def manage_sessions():
    if g.current_user is None:
        return redirect(url_for('login'))

    master_id = request.args.get('master_id', '')
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'asc')

    if g.user_role == 'admin':
        sessions_query = db.session.query(Sessions).join(Addresses)
        masters = db.session.query(User.master_id, User.name_master).distinct()
    else:
        sessions_query = db.session.query(Sessions).filter(Sessions.master_id == g.current_user.master_id).join(Addresses)
        masters = db.session.query(User.master_id, User.name_master).filter(User.master_id == g.current_user.master_id).distinct()

    if master_id:
        sessions_query = sessions_query.filter(Sessions.master_id == g.current_user.master_id)


    if sort_by == 'name_master':
        sessions_query = sessions_query.order_by(Sessions.name_master.asc() if order == 'asc' else Sessions.name_master.desc())
    elif sort_by == 'address':
        sessions_query = sessions_query.order_by(Addresses.address.asc() if order == 'asc' else Addresses.address.desc())
    elif sort_by == 'date':
        sessions_query = sessions_query.order_by(Sessions.date.asc() if order == 'asc' else Sessions.date.desc())

    sessions_list = sessions_query.all()

    formatted_sessions = [
        {
            'id': session_item.id,
            'name_client': session_item.name_client,
            'name_master': session_item.name_master,
            'address': session_item.address,
            'procedure_type': session_item.procedure_type,
            'date': format_datetime(session_item.date, "d MMMM yyyy HH:mm", locale='ru'),
            'payment_status': session_item.payment_status,
            'details': session_item.details,
            'telegram_chat_id': session_item.telegram_chat_id if g.user_role == 'admin' else None,
            'notification_status': session_item.notification_status if g.user_role == 'admin' else None
        }
        for session_item in sessions_list
    ]

    next_order = 'desc' if order == 'asc' else 'asc'

    return render_template('sessions.html', sessions=formatted_sessions, sort_by=sort_by, order=order, next_order=next_order, role=g.user_role, masters=masters, selected_master_id=master_id)



# Управление сеансами
@app.route('/api/sessions')
def api_sessions():
    if g.current_user is None:
        return redirect(url_for('login'))

    # Получаем список сеансов в зависимости от роли пользователя
    if g.user_role == 'admin':
        sessions = Sessions.query.all()
    else:
        sessions = Sessions.query.filter_by(master_id=g.current_user.master_id).all()

    # Формируем список событий
    events = []
    for sess in sessions:
        events.append({
            'title': f"{sess.name_client} - {sess.procedure_type}",
            'start': sess.date.isoformat(),
            'end': (sess.date + timedelta(hours=1)).isoformat(),  # Предполагаем, что сеанс длится 1 час
            'description': sess.details,
            'address': sess.address,
        })
    
    return jsonify(events)




@app.route('/sessions/add', methods=['GET', 'POST'])
def add_session():
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        name_client = request.form.get('name_client')
        master_id = request.form.get('master_id')
        name_master = request.form.get('name_master')
        address_id = request.form.get('address_id')  # Получение ID адреса
        procedure_type = request.form.get('procedure_type')
        date_str = request.form.get('date')
        payment_status = request.form.get('payment_status')
        details = request.form.get('details')
        telegram_chat_id = request.form.get('telegram_chat_id')

        date = datetime.fromisoformat(date_str) if date_str else None

        if not client_id or not master_id or not address_id:
            flash('Выберите клиента, мастера и адрес.', 'error')
        elif not name_client:
            flash('Имя клиента не может быть пустым.', 'error')
        else:
            address = db.session.get(Addresses, address_id)
            if not address:
                flash('Выбранный адрес не найден.', 'error')
            else:
                new_session = Sessions(
                    client_id=client_id,
                    name_client=name_client,
                    master_id=master_id,
                    name_master=name_master,
                    address_id=address_id,
                    address=address.address,  # Устанавливаем значение адреса
                    procedure_type=procedure_type,
                    date=date,
                    payment_status=payment_status,
                    details=details,
                    telegram_chat_id=telegram_chat_id or None
                )
                db.session.add(new_session)
                db.session.commit()
                flash('Сеанс успешно добавлен!', 'success')
                return redirect(url_for('manage_sessions'))

    # Передаем все данные в шаблон, если это GET-запрос
    clients = Client.query.all()
    users = User.query.filter_by(role='master').all()
    addresses = Addresses.query.all()  # Передаем адреса в шаблон
    return render_template('add_session.html', clients=clients, users=users, addresses=addresses)






from flask import g

@app.route('/sessions/edit/<int:session_id>', methods=['GET', 'POST'])
def edit_session(session_id):
    # Проверяем авторизацию и роль пользователя
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    # Получаем запись сеанса из базы данных
    session_record = Sessions.query.get_or_404(session_id)

    if request.method == 'POST':
        # Обновляем поля сеанса на основе данных из формы
        session_record.client_id = request.form.get('client_id')
        session_record.name_client = request.form.get('name_client')
        session_record.master_id = request.form.get('master_id')
        session_record.name_master = request.form.get('name_master')
        address_id = request.form.get('address_id')  # Используем address_id вместо address
        session_record.address_id = address_id
        session_record.procedure_type = request.form.get('procedure_type')
        date_str = request.form.get('date')
        session_record.payment_status = request.form.get('payment_status')
        session_record.details = request.form.get('details')
        session_record.telegram_chat_id = request.form.get('telegram_chat_id')

        # Преобразуем дату из строки в объект datetime
        session_record.date = datetime.fromisoformat(date_str) if date_str else None

        # Проверяем существование адреса
        address = db.session.get(Addresses, address_id)
        if not address:
            flash('Выбранный адрес не найден.', 'error')
            return render_template(
                'edit_session.html',
                session=session_record,
                clients=Client.query.all(),
                users=User.query.filter_by(role='master').all(),
                addresses=Addresses.query.all()
            )

        # Обновляем адрес сеанса
        session_record.address = address.address

        # Сохраняем изменения в базе данных
        db.session.commit()
        flash('Данные сеанса успешно обновлены!', 'success')
        return redirect(url_for('manage_sessions'))

    # Передаем данные в шаблон для страницы редактирования сеанса
    clients = Client.query.all()
    users = User.query.filter_by(role='master').all()
    addresses = Addresses.query.all()
    return render_template(
        'edit_session.html',
        session=session_record,
        clients=clients,
        users=users,
        addresses=addresses
    )





@app.route('/sessions/notify/<int:session_id>', methods=['GET', 'POST'])
def send_notification(session_id):
    # Проверка авторизации
    if g.current_user is None:
        return redirect(url_for('login'))
    
    session_record = Sessions.query.get_or_404(session_id)
    client = Client.query.get_or_404(session_record.client_id)

    if request.method == 'POST':
        option = request.form.get('notification_option')
        template_message = request.form.get('template_message', '')

        # Формирование финального сообщения
        if option == 'custom':
            final_message = template_message
        else:
            final_message = template_message.replace("{client_name}", client.name_client) \
                                            .replace("{procedure_type}", session_record.procedure_type) \
                                            .replace("{master_name}", session_record.name_master) \
                                            .replace("{session_date}", str(session_record.date)) \
                                            .replace("{address}", session_record.address)

        # Отправка уведомления немедленно
        if option in ['send_now', 'send_both', 'custom']:
            if session_record.telegram_chat_id:
                send_message(session_record.telegram_chat_id, final_message)
                session_record.notification_status = 'Отправлено'
            else:
                flash('Не удалось отправить уведомление: ID чата не указан.', 'danger')

        # Запланировать уведомление на день до сеанса
        if option in ['send_day_before', 'send_both']:
            reminder_date = session_record.date - timedelta(days=1)
            if session_record.telegram_chat_id:
                job_id = f'{session_id}_{reminder_date.isoformat()}'
                if not scheduler.get_job(job_id):
                    print(f"Добавление задачи {job_id} в планировщик.")
                    scheduler.add_job(
                        send_delayed_notification,
                        DateTrigger(run_date=reminder_date),
                        id=job_id,
                        args=[session_id, final_message, session_record.telegram_chat_id, job_id]
                    )
                    add_task_to_file(job_id, reminder_date, session_id, final_message, session_record.telegram_chat_id)
                    session_record.notification_status = 'Запланировано'
                else:
                    print(f"Задача {job_id} уже существует.")
            else:
                flash('Не удалось запланировать уведомление: ID чата не указан.', 'danger')

        db.session.commit()
        flash('Уведомление отправлено!', 'success')
        return redirect(url_for('manage_sessions'))

    # Отображение формы
    return render_template(
        'send_notification.html', 
        session=session_record, 
        client=client,
        template_message="Здравствуйте, {client_name}!\nВаш сеанс {procedure_type} у мастера {master_name} назначен на {session_date} по адресу {address}."
    )


@app.route('/sessions/delete/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if g.current_user is None or g.user_role != 'admin':
        return redirect(url_for('login'))

    session_record = Sessions.query.get_or_404(session_id)
    db.session.delete(session_record)
    db.session.commit()
    flash('Сеанс успешно удален!', 'success')
    return redirect(url_for('manage_sessions'))






# Календарь
@app.route('/calendar')
def calendar():
    if g.current_user is None:
        return redirect(url_for('login'))

    if g.user_role == 'admin':
        sessions = Sessions.query.all()
    else:
        sessions = Sessions.query.filter_by(master_id=g.current_user.master_id).all()
    
    # Подготовка данных для календаря
    events = [
        {
            'title': f"{s.name_client} - {s.procedure_type}",
            'start': s.date.isoformat(),
            'end': (s.date + timedelta(hours=1)).isoformat()  # Предположим, сеанс длится 1 час
        } for s in sessions
    ]
    
    return render_template('calendar.html', sessions=events)


# Выход
@app.route('/logout')
def logout():
    # Удаляем данные пользователя из сессии
    session.pop('user_id', None)
    session.pop('role', None)
    
    # Добавляем сообщение об успешном выходе
    flash('Вы успешно вышли из системы.', 'success')
    
    # Перенаправляем на главную страницу
    return redirect(url_for('index'))


def initialize_scheduler():
    if not scheduler.running:
        tasks = load_tasks_from_file()
        for task in tasks:
            try:
                if not scheduler.get_job(task['task_id']):
                    print(f"Добавление задачи {task['task_id']} в планировщик.")
                    scheduler.add_job(
                        send_delayed_notification,
                        DateTrigger(run_date=datetime.fromisoformat(task['run_date'])),
                        id=task['task_id'],
                        args=[task['session_id'], task['final_message'], task['chat_id'], task['task_id']]
                    )
                else:
                    print(f"Задача {task['task_id']} уже существует.")
            except Exception as e:
                print(f"Ошибка при добавлении задачи: {e}")
        scheduler.start()




if __name__ == '__main__':
    initialize_scheduler()
    app.run(debug=True)
