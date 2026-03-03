# Red Alert → Telegram Family Check-in (MVP + Admin UI)

Includes:
- Pikud HaOref polling (`alerts.json`)
- All-clear detection (quiet period)
- Telegram check-in with buttons ✅ OK / ❗ HELP
- Admin UI: view statuses + send TEST check-in

## Env vars (Railway / VPS)
Required:
- TELEGRAM_BOT_TOKEN
- PUBLIC_BASE_URL (e.g. https://your-service.up.railway.app)
- ADMIN_TOKEN (random long string)

Optional:
- POLL_INTERVAL_SECONDS (default 2)
- ALL_CLEAR_AFTER_SECONDS (default 600)
- ADMIN_TELEGRAM_CHAT_ID
- DB_PATH (default data.sqlite)

## Admin UI
Open:
- /admin?token=ADMIN_TOKEN

Send a test check-in:
- POST /admin/send_test_checkin?token=ADMIN_TOKEN

## Telegram webhook
```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$PUBLIC_BASE_URL/telegram/webhook"
```

Verify:
```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

## Family join link
https://t.me/<YOUR_BOT_USERNAME>?start=FAMILY123
