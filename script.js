// ====================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ======================
let currentUser = null;
let examples = [];
let userAnswers = [];
let answered = false;

// ====================== ОСНОВНОЙ МОДУЛЬ ======================
document.addEventListener('DOMContentLoaded', () => {
    AuthModule.checkAuthState();
    EventModule.initEventListeners();
    ExampleModule.generateExamples(); // Первоначальная генерация примеров
});

// ====================== МОДУЛЬ СОБЫТИЙ ======================
const EventModule = {
    initEventListeners: function() {
        // Авторизация
        document.getElementById('login-btn').addEventListener('click', AuthModule.login);
        document.getElementById('register-btn').addEventListener('click', AuthModule.register);
        document.getElementById('guest-btn').addEventListener('click', AuthModule.continueAsGuest);

        // Основной интерфейс
        const modeRadios = document.querySelectorAll('input[name="mode"]');
        modeRadios.forEach(radio => {
            radio.addEventListener('change', () => ExampleModule.handleModeChange());
        });
        document.getElementById('number').addEventListener('change', () => ExampleModule.handleNumberChange());
        document.getElementById('check-btn').addEventListener('click', () => ExampleModule.handleCheckButton());
        document.getElementById('next-btn').addEventListener('click', () => ExampleModule.handleNextButton());
        document.getElementById('repeat-btn').addEventListener('click', () => ExampleModule.handleRepeatButton());
        document.getElementById('logout-btn').addEventListener('click', AuthModule.logout);

        // Профиль
        document.getElementById('profile-btn').addEventListener('click', () => ProfileModule.showProfile());
        document.getElementById('back-btn').addEventListener('click', () => ProfileModule.hideProfile());
    }
};

// ====================== МОДУЛЬ АВТОРИЗАЦИИ ======================
const AuthModule = {
    checkAuthState: function() {
        const savedUserId = localStorage.getItem('user_id');
        if (savedUserId) {
            currentUser = parseInt(savedUserId);
            document.getElementById('auth-screen').style.display = 'none';
            document.getElementById('app-content').style.display = 'block';
            ExampleModule.generateExamples();
        }
    },

    login: async function() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            
            if (data.success) {
                currentUser = data.user_id;
                localStorage.setItem('user_id', data.user_id);
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('app-content').style.display = 'block';
                ExampleModule.generateExamples();
            } else {
                UIHelper.showError(data.error || 'Ошибка авторизации');
            }
        } catch (err) {
            UIHelper.showError('Сервер недоступен');
        }
    },

    register: async function() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            
            if (data.success) {
                UIHelper.showSuccess('Регистрация успешна! Войдите в систему');
            } else {
                UIHelper.showError('Ошибка регистрации');
            }
        } catch (err) {
            UIHelper.showError('Сервер недоступен');
        }
    },

    continueAsGuest: function() {
        currentUser = 'guest';
        document.getElementById('auth-screen').style.display = 'none';
        document.getElementById('app-content').style.display = 'block';
        ExampleModule.generateExamples();
    },

    logout: function() {
        currentUser = null;
        localStorage.removeItem('user_id');
        document.getElementById('app-content').style.display = 'none';
        document.getElementById('auth-screen').style.display = 'block';
        document.getElementById('password').value = '';
    }
};

// ====================== МОДУЛЬ ПРИМЕРОВ ======================
const ExampleModule = {
    handleModeChange: function() {
        this.generateExamples();
    },

    handleNumberChange: function() {
        this.generateExamples();
    },

    generateExamples: async function() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const number = parseInt(document.getElementById('number').value);

        try {
            const response = await fetch('/generate-examples', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    mode: mode, 
                    number: number
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            examples = await response.json();
            this.renderExamples();
            UIHelper.hideButtons(); // Скрыть кнопки
            answered = false;

        } catch (err) {
            console.error('Ошибка:', err);
            UIHelper.showError('Ошибка генерации примеров. Используется локальная генерация.');
           
            examples = Array.from({length: 10}, () => ({
                a: Math.floor(Math.random()*8)+2,
                b: Math.floor(Math.random()*8)+2
            }));
            this.renderExamples();
            UIHelper.hideButtons(); // Скрыть кнопки и при ошибке
            answered = false;
        }
    },

    renderExamples: function() {
        const container = document.getElementById('examples');
        container.innerHTML = '';
        userAnswers = [];

        examples.forEach((ex, index) => {
            const example = document.createElement('div');
            example.className = 'example-item';
            example.innerHTML = `
                <p>${ex.a} × ${ex.b} = <input type="number" class="answer-input" data-index="${index}"></p>
            `;
            container.appendChild(example);

            const input = example.querySelector('.answer-input');
            input.addEventListener('input', (e) => {
                userAnswers[index] = parseInt(e.target.value) || 0;
            });
        });

        document.getElementById('result').innerHTML = '';
    },

    handleCheckButton: function() {
        this.checkAnswers();
    },

    handleNextButton: function() {
        this.generateExamples();
         UIHelper.hideButtons(); // Hide buttons after generating new examples
    },

    handleRepeatButton: function() {
        this.renderExamples();
         UIHelper.hideButtons(); // Hide buttons after rendering same examples
    },

    checkAnswers: async function() {
        let correct = 0;
        const results = [];

        examples.forEach((ex, index) => {
            const isCorrect = ex.a * ex.b === userAnswers[index];
            if (isCorrect) correct++;
            results.push(isCorrect);
        });

        if (currentUser && currentUser !== 'guest') {
            try {
                await fetch('/save-result', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: currentUser,
                        score: correct
                    })
                });

                await ProfileModule.updateAchievements(correct);
            } catch (err) {
                console.error('Ошибка сохранения:', err);
            }
        }

        UIHelper.showResult(correct, examples.length, results);
        UIHelper.showButtons(); // Показать кнопки после проверки
    }
};

// ====================== МОДУЛЬ ПРОФИЛЯ ======================
const ProfileModule = {
    
    showProfile: async function() {
        document.getElementById('app-content').style.display = 'none';
        document.getElementById('profile-content').style.display = 'block';

        if (currentUser && currentUser !== 'guest') {
            try {
                const response = await fetch(`/profile/${currentUser}`);
                if (!response.ok) throw new Error('Ошибка загрузки');
                
                const data = await response.json();
                this.renderProfile(data);
            } catch (err) {
                document.getElementById('achievements-list').innerHTML = 
                    '<p class="error-message">Ошибка загрузки профиля</p>';
            }
        } else {
            this.renderGuestProfile();
        }
    },

    renderProfile: function(data) {
        document.getElementById('profile-username').textContent = data.username;
        document.getElementById('profile-level').textContent = data.level;
        document.getElementById('total-score').textContent = data.total_score;
        
        const list = document.getElementById('achievements-list');
        list.innerHTML = data.achievements.length > 0 ? '' : '<p>Нет достижений</p>';
        
        data.achievements.forEach(ach => {
            const item = document.createElement('div');
            item.className = 'achievement-item';
            item.innerHTML = `
                <div>
                    <strong>${ach.name}</strong>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${ach.progress}%"></div>
                    </div>
                </div>
                <span>${ach.progress}%</span>
            `;
            list.appendChild(item);
        });
    },

    renderGuestProfile: function() {
        document.getElementById('profile-username').textContent = 'Гость';
        document.getElementById('profile-level').textContent = '1';
        document.getElementById('total-score').textContent = '0';
        document.getElementById('achievements-list').innerHTML = 
            '<p>Доступно только для авторизованных пользователей</p>';
    },

    hideProfile: function() {
        document.getElementById('profile-content').style.display = 'none';
        document.getElementById('app-content').style.display = 'block';
    },

    updateAchievements: async function(score) {
        const progress = Math.min(100, Math.floor(score / examples.length * 100));
        
        try {
            await fetch('/update-achievement', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: currentUser,
                    name: 'Решатель примеров',
                    progress: progress
                })
            });
        } catch (err) {
            console.error('Ошибка обновления достижений:', err);
        }
    }
};

// ====================== UI HELPER MODULE ======================
const UIHelper = {
    showError: function(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        document.getElementById('auth-form').prepend(errorElement);
        setTimeout(() => errorElement.remove(), 3000);
    },

    showSuccess: function(message) {
        const successElement = document.createElement('div');
        successElement.className = 'success-message';
        successElement.textContent = message;
        document.getElementById('auth-form').prepend(successElement);
        setTimeout(() => successElement.remove(), 3000);
    },

    showResult: function(correct, total, results) {
        const resultContainer = document.getElementById('result');
        resultContainer.innerHTML = `
            <div class="success-message">
                Правильно: ${correct} из ${total}
            </div>
        `;

        const exampleItems = document.querySelectorAll('.example-item');
        exampleItems.forEach((item, index) => {
            item.style.backgroundColor = results[index] ? '#e8f5e9' : '#ffebee';
        });
    },

    showButtons: function() {
        document.getElementById('next-btn').style.display = 'inline-block';
        document.getElementById('repeat-btn').style.display = 'inline-block';
    },

    hideButtons: function() {
        document.getElementById('next-btn').style.display = 'none';
        document.getElementById('repeat-btn').style.display = 'none';
    }
};
