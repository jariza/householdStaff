FROM python:3.14

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY main.py messages.json requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]