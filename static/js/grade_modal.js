document.addEventListener('DOMContentLoaded', function() {
    // Элементы модального окна
    const modal = document.getElementById('markModal');
    const openBtn = document.getElementById('openModalBtn');
    const closeBtn = document.querySelector('.close-btn');
    const cancelBtn = document.querySelector('.btn-secondary');
    const saveBtn = document.getElementById('saveBtn');
    const addMarkBtn = document.querySelector('.add-mark-btn');
    const markOptions = document.querySelectorAll('input[name="mark"]');
    const commentInput = document.querySelector('.comment-input');
    const attendanceToggle = document.getElementById('attendanceToggle');
    const statusSelect = document.querySelector('.status-select');
    const deleteMarkBtn = document.querySelector('.delete-mark-btn');

    // Открытие модального окна
    openBtn.addEventListener('click', () => {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        // При открытии кнопка удаления неактивна
        deleteMarkBtn.disabled = true;
    });

    // Закрытие модального окна
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Закрытие при клике вне окна
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    // Обработка выбора оценки
    markOptions.forEach(option => {
        option.addEventListener('change', function() {
            console.log('Выбрана оценка:', this.value);
            // Активируем кнопку удаления при выборе оценки
            deleteMarkBtn.disabled = false;
            deleteMarkBtn.title = "Удалить выбранную оценку";
        });
    });

    // Кнопка удаления оценки
    deleteMarkBtn.addEventListener('click', function() {
        if (this.disabled) return;

        const selectedMark = document.querySelector('input[name="mark"]:checked');

        if (!selectedMark) {
            alert('Нет выбранной оценки для удаления');
            return;
        }

        // Подтверждение удаления
        if (confirm(`Удалить оценку ${selectedMark.value}?`)) {
            // Снимаем выбор оценки
            selectedMark.checked = false;

            // Деактивируем кнопку удаления
            this.disabled = true;
            this.title = "Выберите оценку для удаления";

            console.log('Оценка удалена');

            // Можно добавить дополнительные действия
            // Например, скрыть соответствующую отметку в интерфейсе
        }
    });

    // Обработчик изменения типа оценки
    statusSelect.addEventListener('change', function() {
        const selectedValue = this.value;
        const selectedText = this.options[this.selectedIndex].text;
        console.log('Тип оценки изменен:', selectedValue, '(', selectedText, ')');
    });

    // Обработчик изменения переключателя посещаемости
    attendanceToggle.addEventListener('change', function() {
        const status = this.checked ? 'Был' : 'Не был';
        console.log('Статус посещения изменен на:', status);
    });

    // Кнопка "Еще отметка"
    addMarkBtn.addEventListener('click', function() {
        alert('Функционал "Еще отметка" в разработке. Здесь можно добавить форму для дополнительной отметки.');
    });

    // Кнопка "Сохранить"
    saveBtn.addEventListener('click', function() {
        const selectedMark = document.querySelector('input[name="mark"]:checked');
        const comment = commentInput.value.trim();
        const wasPresent = attendanceToggle.checked;
        const markType = statusSelect.value;
        const markTypeText = statusSelect.options[statusSelect.selectedIndex].text;

        if (!selectedMark) {
            alert('Пожалуйста, выберите оценку!');
            return;
        }

        // Собираем данные
        const data = {
            student: 'Закиров Асхат',
            mark: selectedMark.value,
            markType: markType,
            markTypeText: markTypeText,
            comment: comment || 'Нет комментария',
            attendance: wasPresent ? 'Был' : 'Не был',
            attendanceStatus: wasPresent
        };

        console.log('Данные для сохранения:', data);

        // Форматированное сообщение
        const message = `Данные сохранены:\n
        Студент: ${data.student}
        Оценка: ${data.mark}
        Тип оценки: ${data.markTypeText}
        Посещение: ${data.attendance}
        Комментарий: "${data.comment}"`;

        alert(message);

        // Здесь обычно отправляем данные на сервер
        // fetch('/api/save-mark', {
        //     method: 'POST',
        //     headers: {'Content-Type': 'application/json'},
        //     body: JSON.stringify(data)
        // })

        closeModal();

        // Сброс формы
        resetForm();
    });

    // Функция сброса формы
    function resetForm() {
        const selectedMark = document.querySelector('input[name="mark"]:checked');
        if (selectedMark) selectedMark.checked = false;
        commentInput.value = '';
        attendanceToggle.checked = false;
        statusSelect.value = 'not-selected';
        deleteMarkBtn.disabled = true;
        deleteMarkBtn.title = "Выберите оценку для удаления";
    }

    // Закрытие по клавише ESC
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal.style.display === 'flex') {
            closeModal();
        }
    });
});


// document.addEventListener('DOMContentLoaded', function() {
//     // Элементы модального окна
//     const modal = document.getElementById('markModal');
//     const openBtn = document.getElementById('openModalBtn');
//     const closeBtn = document.querySelector('.close-btn');
//     const cancelBtn = document.querySelector('.btn-secondary');
//     const saveBtn = document.getElementById('saveBtn');
//     const addMarkBtn = document.querySelector('.add-mark-btn');
//     const markOptions = document.querySelectorAll('input[name="mark"]');
//     const commentInput = document.querySelector('.comment-input');
//     const attendanceToggle = document.getElementById('attendanceToggle');
//     const statusSelect = document.querySelector('.status-select');
//
//     // Открытие модального окна
//     openBtn.addEventListener('click', () => {
//         modal.style.display = 'flex';
//         document.body.style.overflow = 'hidden';
//     });
//
//     // Закрытие модального окна
//     function closeModal() {
//         modal.style.display = 'none';
//         document.body.style.overflow = 'auto';
//     }
//
//     closeBtn.addEventListener('click', closeModal);
//     cancelBtn.addEventListener('click', closeModal);
//
//     // Закрытие при клике вне окна
//     window.addEventListener('click', (event) => {
//         if (event.target === modal) {
//             closeModal();
//         }
//     });
//
//     // Обработка выбора оценки
//     markOptions.forEach(option => {
//         option.addEventListener('change', function() {
//             console.log('Выбрана оценка:', this.value);
//         });
//     });
//
//     // Обработчик изменения типа оценки
//     statusSelect.addEventListener('change', function() {
//         const selectedValue = this.value;
//         const selectedText = this.options[this.selectedIndex].text;
//         console.log('Тип оценки изменен:', selectedValue, '(', selectedText, ')');
//
//         // Можно добавить логику в зависимости от выбранного типа
//         if (selectedValue === 'exam') {
//             // Например, для экзамена показать дополнительные поля
//             console.log('Выбран экзамен - можно добавить доп. параметры');
//         }
//     });
//
//     // Обработчик изменения переключателя посещаемости
//     attendanceToggle.addEventListener('change', function() {
//         const status = this.checked ? 'Был' : 'Не был';
//         console.log('Статус посещения изменен на:', status);
//     });
//
//     // Кнопка "Еще отметка"
//     addMarkBtn.addEventListener('click', function() {
//         alert('Функционал "Еще отметка" в разработке. Здесь можно добавить форму для дополнительной отметки.');
//     });
//
//     // Кнопка "Сохранить"
//     saveBtn.addEventListener('click', function() {
//         const selectedMark = document.querySelector('input[name="mark"]:checked');
//         const comment = commentInput.value.trim();
//         const wasPresent = attendanceToggle.checked;
//         const markType = statusSelect.value;
//         const markTypeText = statusSelect.options[statusSelect.selectedIndex].text;
//
//         if (!selectedMark) {
//             alert('Пожалуйста, выберите оценку!');
//             return;
//         }
//
//         // Собираем данные
//         const data = {
//             student: 'Закиров Асхат',
//             mark: selectedMark.value,
//             markType: markType,
//             markTypeText: markTypeText,
//             comment: comment || 'Нет комментария',
//             attendance: wasPresent ? 'Был' : 'Не был',
//             attendanceStatus: wasPresent
//         };
//
//         console.log('Данные для сохранения:', data);
//
//         // Форматированное сообщение
//         const message = `Данные сохранены:\n
//         Студент: ${data.student}
//         Оценка: ${data.mark}
//         Тип оценки: ${data.markTypeText}
//         Посещение: ${data.attendance}
//         Комментарий: "${data.comment}"`;
//
//         alert(message);
//
//         // Здесь обычно отправляем данные на сервер
//         // fetch('/api/save-mark', {
//         //     method: 'POST',
//         //     headers: {'Content-Type': 'application/json'},
//         //     body: JSON.stringify(data)
//         // })
//
//         closeModal();
//
//         // Сброс формы (опционально)
//         resetForm();
//     });
//
//     // Функция сброса формы
//     function resetForm() {
//         const selectedMark = document.querySelector('input[name="mark"]:checked');
//         if (selectedMark) selectedMark.checked = false;
//         commentInput.value = '';
//         attendanceToggle.checked = false;
//         statusSelect.value = 'not-selected';
//     }
//
//     // Закрытие по клавише ESC
//     document.addEventListener('keydown', (event) => {
//         if (event.key === 'Escape' && modal.style.display === 'flex') {
//             closeModal();
//         }
//     });
// });

// document.addEventListener('DOMContentLoaded', function() {
//     // Элементы модального окна
//     const modal = document.getElementById('markModal');
//     const openBtn = document.getElementById('openModalBtn');
//     const closeBtn = document.querySelector('.close-btn');
//     const cancelBtn = document.querySelector('.btn-secondary');
//     const saveBtn = document.getElementById('saveBtn');
//     const addMarkBtn = document.querySelector('.add-mark-btn');
//     const markOptions = document.querySelectorAll('input[name="mark"]');
//     const commentInput = document.querySelector('.comment-input');
//     const attendanceToggle = document.getElementById('attendanceToggle');
//
//     // Открытие модального окна
//     openBtn.addEventListener('click', () => {
//         modal.style.display = 'flex';
//         document.body.style.overflow = 'hidden'; // Блокируем скролл страницы
//     });
//
//     // Закрытие модального окна
//     function closeModal() {
//         modal.style.display = 'none';
//         document.body.style.overflow = 'auto';
//     }
//
//     closeBtn.addEventListener('click', closeModal);
//     cancelBtn.addEventListener('click', closeModal);
//
//     // Закрытие при клике вне окна
//     window.addEventListener('click', (event) => {
//         if (event.target === modal) {
//             closeModal();
//         }
//     });
//
//     // Обработка выбора оценки
//     markOptions.forEach(option => {
//         option.addEventListener('change', function() {
//             console.log('Выбрана оценка:', this.value);
//             // Здесь можно добавить логику, например, изменение цвета статуса
//         });
//     });
//
//     // Кнопка "Еще отметка"
//     addMarkBtn.addEventListener('click', function() {
//         alert('Функционал "Еще отметка" в разработке. Здесь можно добавить форму для дополнительной отметки.');
//         // Логика для добавления новой формы оценки
//     });
//
//     // Кнопка "Сохранить"
//     saveBtn.addEventListener('click', function() {
//         const selectedMark = document.querySelector('input[name="mark"]:checked');
//         const comment = commentInput.value.trim();
//         const wasPresent = attendanceToggle.checked;
//
//         if (!selectedMark) {
//             alert('Пожалуйста, выберите оценку!');
//             return;
//         }
//
//         // Собираем данные
//         const data = {
//             student: 'Закиров Асхат',
//             mark: selectedMark.value,
//             comment: comment || 'Нет комментария',
//             attendance: wasPresent ? 'Был' : 'Не был',
//             attendanceStatus: wasPresent // true/false для логики
//         };
//
//         console.log('Данные для сохранения:', data);
//         alert(`Оценка ${data.mark} сохранена! Студент: ${data.attendance}. Комментарий: "${data.comment}"`);
//
//         // Здесь обычно отправляем данные на сервер
//         // fetch('/api/save-mark', { method: 'POST', body: JSON.stringify(data) })
//
//         closeModal();
//
//         // Сброс формы (опционально)
//         selectedMark.checked = false;
//         commentInput.value = '';
//         attendanceToggle.checked = false; // Сброс в "Не был"
//     });
//
//     // Закрытие по клавише ESC
//     attendanceToggle.addEventListener('change', function() {
//         console.log('Статус посещения:', this.checked ? 'Был' : 'Не был');
//         // Можно добавить дополнительную логику при переключении
//     });
// });