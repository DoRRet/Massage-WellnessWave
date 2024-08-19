#create_users.py
from app import db, User, app

def create_users():
    # Создаем пользователей
    admin = User(username='admin', password='admin', role='admin')
    therapist = User(username='therapist', password='therapist', role='therapist')
    receptionist = User(username='receptionist', password='receptionist', role='receptionist')

    with app.app_context():
        db.create_all()  # Создаем таблицы
        db.session.add(admin)
        db.session.add(therapist)
        db.session.add(receptionist)
        db.session.commit()

if __name__ == '__main__':
    create_users()
