#!/usr/bin/env bash
# Выкладка бота на сервер. Запускать с вашего компьютера из папки проекта:
#   ./deploy.sh root@79.132.143.211
# Пароль (или ключ) SSH вводите вы сами. Повторный запуск = обновление.
set -euo pipefail

HOST="${1:?Использование: ./deploy.sh user@host}"
DIR=/home/bots/fundraising
SSH_OPTS="-o ControlMaster=auto -o ControlPath=/tmp/fundraising-deploy-%r@%h:%p -o ControlPersist=120"

run() { ssh $SSH_OPTS "$HOST" "$@"; }

run "mkdir -p $DIR"
rsync -az --delete -e "ssh $SSH_OPTS" \
    --exclude '.git' --exclude '.idea' --exclude '.venv' --exclude '__pycache__' \
    --exclude 'data' --exclude '.env' --exclude '*.db' \
    ./ "$HOST:$DIR/"

run "DIR=$DIR bash -s" <<'REMOTE'
set -euo pipefail
cd "$DIR"

if ! python3 -m venv .venv 2>/dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-venv
    python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo
    echo ">>> Создан $DIR/.env. Впишите BOT_TOKEN и ADMIN_CHAT_ID:"
    echo ">>>   nano $DIR/.env"
    echo ">>> затем запустите ./deploy.sh ещё раз."
    exit 0
fi

cp fundraising-bot.service /etc/systemd/system/fundraising-bot.service
systemctl daemon-reload
systemctl enable fundraising-bot >/dev/null 2>&1
systemctl restart fundraising-bot
sleep 2
systemctl --no-pager --lines=15 status fundraising-bot || true
REMOTE
