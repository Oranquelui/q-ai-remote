#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "Language / 言語"
echo "  1) 日本語"
echo "  2) English"
read -r -p "Select [1/2] (default: 1): " LANG_CHOICE
case "${LANG_CHOICE:-1}" in
  2|en|EN|english|English)
    LANG_CODE="en"
    ;;
  *)
    LANG_CODE="ja"
    ;;
esac

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  if [[ "$LANG_CODE" == "ja" ]]; then
    echo "[ERROR] Pythonが見つかりません。先にPython 3をインストールしてください。"
    read -r -p "Enterで閉じます..."
  else
    echo "[ERROR] Python not found. Install Python 3 first."
    read -r -p "Press Enter to close..."
  fi
  exit 1
fi

if [[ "$LANG_CODE" == "ja" ]]; then
  echo "[INFO] Telegram Botトークン（BotFather発行）は必須です。"
  echo "       Telegramで操作するBotのトークンを設定してください。"
else
  echo "[INFO] Telegram bot token from BotFather is required."
  echo "       Set the token for the bot you will actually message in Telegram."
fi
echo

set +e
"$PYTHON_BIN" "$ROOT_DIR/scripts/setup_wizard.py" --lang "$LANG_CODE"
RC=$?
set -e
echo
if [[ $RC -eq 0 ]]; then
  ACTIVE_INSTANCE_FILE="$ROOT_DIR/config/.active_instance"
  if [[ -f "$ACTIVE_INSTANCE_FILE" ]]; then
    INSTANCE_ID="$(tr -d '\r\n' < "$ACTIVE_INSTANCE_FILE")"
  else
    INSTANCE_ID="default"
  fi
  if [[ -z "$INSTANCE_ID" ]]; then
    INSTANCE_ID="default"
  fi

  AUTOSTART="${QCA_SETUP_AUTOSTART:-Y}"
  case "$AUTOSTART" in
    n|N|no|NO|0|false|FALSE)
      START_NOW="N"
      ;;
    *)
      START_NOW="Y"
      ;;
  esac

  if [[ "$LANG_CODE" == "ja" ]]; then
    echo "[OK] セットアップ完了"
    if [[ "$START_NOW" == "N" ]]; then
      read -r -p "Enterで閉じます..."
      exit 0
    fi
    echo "[INFO] Botを自動起動します... (instance_id=$INSTANCE_ID)"
  else
    echo "[OK] setup completed"
    if [[ "$START_NOW" == "N" ]]; then
      read -r -p "Press Enter to close..."
      exit 0
    fi
    echo "[INFO] Starting bot automatically... (instance_id=$INSTANCE_ID)"
  fi

  RUN_PATTERN="src.main --instance-id $INSTANCE_ID"
  EXISTING_PIDS="$(pgrep -f "$RUN_PATTERN" || true)"
  if [[ -n "$EXISTING_PIDS" ]]; then
    if [[ "$LANG_CODE" == "ja" ]]; then
      echo "[INFO] 同じinstance_idのBotプロセスを停止して再起動します..."
    else
      echo "[INFO] Stopping existing bot process for same instance_id before restart..."
    fi
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      kill "$pid" >/dev/null 2>&1 || true
    done <<< "$EXISTING_PIDS"
    sleep 1
  fi

  set +e
  "$PYTHON_BIN" -m src.main --instance-id "$INSTANCE_ID"
  BOT_RC=$?
  set -e
  echo
  if [[ "$LANG_CODE" == "ja" ]]; then
    echo "[INFO] Botが終了しました (code=$BOT_RC)"
    read -r -p "Enterで閉じます..."
  else
    echo "[INFO] Bot stopped (code=$BOT_RC)"
    read -r -p "Press Enter to close..."
  fi
  exit $BOT_RC
else
  if [[ "$LANG_CODE" == "ja" ]]; then
    echo "[ERROR] セットアップ失敗 (code=$RC)"
  else
    echo "[ERROR] setup failed (code=$RC)"
  fi
fi
if [[ "$LANG_CODE" == "ja" ]]; then
  read -r -p "Enterで閉じます..."
else
  read -r -p "Press Enter to close..."
fi
exit $RC
