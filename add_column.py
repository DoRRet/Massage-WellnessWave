import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('instance/wellnesswave.db')  # Убедитесь, что имя файла базы данных верное
cursor = conn.cursor()

# Выполнение SQL-запроса для добавления нового столбца
cursor.execute('ALTER TABLE Sessions ADD COLUMN notification_status TEXT;')

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Колонка 'notification_status' успешно добавлена в таблицу 'sessions'.")
