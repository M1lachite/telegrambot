FROM alpine

RUN apk apk update && \
    apk add --no-cache python3 py3-pip && \
    pip3 install pyTelegrambotAPI --break-system-packages && \
    mkdir /app

COPY telegram_bot.py /app/telegram_bot.py

WORKDIR /app

CMD [ "python3", "telegram_bot.py" ]