# Telegram Setup for Custodian

Custodian sends **critical-only** alerts to your phone via Telegram.
(Warnings appear in the dashboard and daily email only.)

## Steps

1. Open Telegram and search for `@BotFather`. Start a chat.

2. Send `/newbot`. Follow the prompts:
   - Name: e.g. `Keepsake Custodian`
   - Username: e.g. `keepsake_custodian_bot` (must end in `bot`)

3. BotFather sends you a token. Copy it — you will not see it again.

4. Open a chat with your new bot. Send any message (e.g. `hi`).
   This is required for the bot to know your chat ID.

5. In a browser, visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Find your chat ID in the response:
   ```json
   {"message": {"chat": {"id": 123456789}}}
   ```

6. Add these two lines to `mac/.env`:
   ```
   KEEPSAKE_TELEGRAM_BOT_TOKEN=your-token-here
   KEEPSAKE_TELEGRAM_CHAT_ID=123456789
   ```

7. Test the connection:
   ```bash
   cd /Users/sangjunyooart/keepsake-migration
   source mac/venv/bin/activate
   python -m helper.custodian.alerts.telegram_pusher --test
   ```
   You should receive a test message on your phone within a few seconds.

## What you will receive

**Critical alerts only:**
- Ethics filter leak detected (chunk auto-quarantined, lens training paused)
- Pi unreachable for 24+ hours
- Push failing 5+ consecutive times
- All lenses idle for 24+ hours

**Rate limit:** same critical type does not push more than once per 6 hours.

**Warnings** (stale training, slow data flow, etc.) appear in the
daily email and dashboard only — not on Telegram.
