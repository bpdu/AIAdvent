# Dockerfile для мониторинга хоста
# День 15: Environment - Агент + Docker

FROM python:3.10-slim

# Установка зависимостей
RUN pip install --no-cache-dir flask psutil

# Создать рабочую директорию
WORKDIR /app

# Скопировать приложение
COPY app.py /app/

# Открыть порт 8001
EXPOSE 8001

# Запустить Flask приложение
CMD ["python", "app.py"]
