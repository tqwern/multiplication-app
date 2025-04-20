from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import bcrypt
import os
from contextlib import closing
import random
import secrets
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)
app.secret_key = secrets.token_hex(32)

DATABASE_FILE = 'database.db'

def init_db():
    with closing(sqlite3.connect(DATABASE_FILE)) as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    user_id INTEGER,
                    score INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    user_id INTEGER,
                    name TEXT,
                    progress INTEGER,
                    UNIQUE(user_id, name),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    level INTEGER DEFAULT 1,
                    total_score INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
    logging.info("База данных инициализирована")

def recreate_db():
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        logging.info("Старая база данных удалена")
    init_db()
    logging.info("Новая база данных создана")

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        logging.warning("Попытка регистрации с неполными данными")
        return jsonify({'error': 'Необходимо указать имя пользователя и пароль'}), 400

    try:
        password_encoded = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_encoded, bcrypt.gensalt())

        with closing(sqlite3.connect(DATABASE_FILE)) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, hashed.decode('utf-8'))
                )
                user_id = cursor.lastrowid
                cursor.execute(
                    'INSERT INTO profiles (user_id) VALUES (?)',
                    (user_id,)
                )
                cursor.execute(
                    'INSERT INTO achievements (user_id, name, progress) VALUES (?, ?, ?)',
                    (user_id, 'Новичок', 0)
                )
        logging.info(f"Зарегистрирован новый пользователь: {username} с id: {user_id}")
        return jsonify({'success': True, 'user_id': user_id})
    except sqlite3.IntegrityError:
        logging.warning(f"Попытка регистрации с занятым именем: {username}")
        return jsonify({'error': 'Имя пользователя уже занято'}), 400
    except Exception as e:
        logging.error(f"Ошибка регистрации: {str(e)}")
        return jsonify({'error': 'Ошибка регистрации'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        logging.warning("Попытка входа с неполными данными")
        return jsonify({'error': 'Необходимо указать имя пользователя и пароль'}), 400

    try:
        password_encoded = password.encode('utf-8')

        with closing(sqlite3.connect(DATABASE_FILE)) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, password FROM users WHERE username = ?',
                    (username,)
                )
                result = cursor.fetchone()

        if not result:
            logging.warning(f"Пользователь не найден: {username}")
            return jsonify({'error': 'Пользователь не найден'}), 400

        user_id, stored_password = result
        if bcrypt.checkpw(password_encoded, stored_password.encode('utf-8')):
            logging.info(f"Пользователь вошел в систему: {username} с id: {user_id}")
            return jsonify({'success': True, 'user_id': user_id})
        else:
            logging.warning(f"Неверный пароль для пользователя: {username}")
            return jsonify({'error': 'Неверный пароль'}), 400
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных при входе: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.error(f"Ошибка при входе: {str(e)}")
        return jsonify({'error': 'Ошибка входа'}), 500

@app.route('/generate-examples', methods=['POST'])
def generate_examples():
    data = request.get_json()
    mode = data.get('mode', 'off')
    number = data.get('number', 2)

    try:
        number = int(number)
        number = max(2, min(9, number))
    except (ValueError, TypeError):
        logging.warning("Некорректное число, используется значение по умолчанию 2")
        number = 2

    examples = []

    if mode == 'on':
        examples = [{"a": number, "b": i} for i in range(2, 10)]
        extra = random.sample([i for i in range(2, 10) if i != number], 2)
        examples.extend({"a": number, "b": i} for i in extra)
    else:
        pairs = [
            {"a": i, "b": j}
            for i in range(2, number + 1)
            for j in range(2, 10)
        ]
        while len(pairs) < 10:
            pairs.extend(pairs)
        examples = random.sample(pairs, 10)

    return jsonify(examples)

@app.route('/save-result', methods=['POST'])
def save_result():
    data = request.get_json()
    user_id = data.get('user_id')
    score = data.get('score')

    if not isinstance(user_id, int) and user_id is not None:
        logging.warning("Некорректный user_id")
        return jsonify({'error': 'Некорректный user_id'}), 400

    try:
        score = int(score)
    except (ValueError, TypeError):
        logging.warning("Некорректный score")
        return jsonify({'error': 'Некорректный score'}), 400

    try:
        with closing(sqlite3.connect(DATABASE_FILE)) as conn:
            with conn:
                if user_id:
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT INTO results (user_id, score) VALUES (?, ?)',
                        (user_id, score)
                    )
                    cursor.execute(
                        'UPDATE profiles SET total_score = total_score + ? WHERE user_id = ?',
                        (score, user_id)
                    )
                    logging.info(f"Результат сохранён для пользователя {user_id}: score {score}")
                else:
                    logging.info(f"Результат гостя сохранён: score {score}")
                    conn.execute(
                        'INSERT INTO results (user_id, score) VALUES (?, ?)',
                        (None, score)
                    )
        return jsonify({'success': True})
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных при сохранении результата: {str(e)}")
        return jsonify({'error': f'Ошибка базы данных: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Ошибка сохранения результата: {str(e)}")
        return jsonify({'error': 'Ошибка сохранения результата'}), 500

@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if not user:
                logging.warning(f"Пользователь с id {user_id} не найден")
                return jsonify({'error': 'Пользователь не найден'}), 404

            # Получаем информацию о профиле
            cursor.execute('''
                SELECT p.level, u.username, p.total_score
                FROM profiles p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
            ''', (user_id,))
            profile = cursor.fetchone()

            if not profile:
                logging.warning(f"Профиль не найден для пользователя {user_id}")
                return jsonify({'error': 'Профиль не найден'}), 404

            # Получаем достижения
            cursor.execute('''
                SELECT name, progress
                FROM achievements
                WHERE user_id = ?
            ''', (user_id,))
            achievements = cursor.fetchall()

            # Формируем ответ
            profile_data = {
                'username': profile['username'],
                'level': profile['level'],
                'total_score': profile['total_score'],
                'achievements': [{'name': a['name'], 'progress': a['progress']} for a in achievements]
            }
            logging.info(f"Профиль получен для пользователя {user_id}")
            return jsonify(profile_data)

    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных при получении профиля: {str(e)}")
        return jsonify({'error': f'Ошибка базы данных: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Ошибка при получении профиля: {str(e)}")
        return jsonify({'error': 'Ошибка получения профиля'}), 500

@app.route('/update-achievement', methods=['POST'])
def update_achievement():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    progress = data.get('progress')

    if not user_id or not name or progress is None:
        logging.warning("Отсутствуют необходимые параметры для обновления достижения")
        return jsonify({'error': 'Отсутствуют необходимые параметры'}), 400

    try:
        user_id = int(user_id)
        progress = int(progress)
        if progress < 0 or progress > 100:
            logging.warning("Прогресс достижения должен быть от 0 до 100")
            return jsonify({'error': 'Прогресс должен быть от 0 до 100'}), 400
    except ValueError:
        logging.warning("Некорректный user_id или progress")
        return jsonify({'error': 'Некорректный user_id или progress'}), 400

    try:
        with closing(sqlite3.connect(DATABASE_FILE)) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO achievements (user_id, name, progress)
                    VALUES (?, ?, ?)
                ''', (user_id, name, min(100, progress)))

                if progress >= 100:
                    cursor.execute('''
                        UPDATE profiles
                        SET level = level + 1
                        WHERE user_id = ?
                    ''', (user_id,))
        logging.info(f"Достижение обновлено для пользователя {user_id}: {name} - {progress}")

        return jsonify({'success': True})
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных при обновлении достижения: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.error(f"Ошибка при обновлении достижения: {str(e)}")
        return jsonify({'error': 'Ошибка обновления достижения'}), 500

# Статические файлы
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../frontend', filename)

if __name__ == '__main__':
    #recreate_db()  # Раскомментируйте для пересоздания базы данных при каждом запуске
    app.run(port=3000, debug=True)
