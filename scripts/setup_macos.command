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
    echo "[INFO] Botを自動起動します..."
  else
    echo "[OK] setup completed"
    if [[ "$START_NOW" == "N" ]]; then
      read -r -p "Press Enter to close..."
      exit 0
    fi
    echo "[INFO] Starting bot automatically..."
  fi

  AUTOSTART_SCOPE="${QCA_SETUP_AUTOSTART_SCOPE:-active}"
  case "$AUTOSTART_SCOPE" in
    all|ALL|All)
      TARGET_SCOPE="all"
      ;;
    *)
      TARGET_SCOPE="active"
      ;;
  esac

  if [[ "$TARGET_SCOPE" == "all" ]]; then
    if [[ "$LANG_CODE" == "ja" ]]; then
      echo "[INFO] 登録済みBotをすべて再起動します (scope=all)"
    else
      echo "[INFO] Restarting all registered bots (scope=all)"
    fi
    set +e
    "$PYTHON_BIN" "$ROOT_DIR/scripts/bot_manager.py" start --all --restart --python-bin "$PYTHON_BIN"
    BOT_RC=$?
    set -e
  else
    if [[ "$LANG_CODE" == "ja" ]]; then
      echo "[INFO] 対象インスタンスを再起動します (instance_id=$INSTANCE_ID)"
    else
      echo "[INFO] Restarting target instance (instance_id=$INSTANCE_ID)"
    fi
    set +e
    "$PYTHON_BIN" "$ROOT_DIR/scripts/bot_manager.py" restart --instance-id "$INSTANCE_ID" --python-bin "$PYTHON_BIN"
    BOT_RC=$?
    set -e
  fi

  echo
  if [[ $BOT_RC -eq 0 ]]; then
    if [[ "$LANG_CODE" == "ja" ]]; then
      echo "[OK] Botマネージャ起動完了"
      echo "[INFO] 状態確認: $PYTHON_BIN $ROOT_DIR/scripts/bot_manager.py status --all"
      echo "[INFO] ログ確認: tail -f $ROOT_DIR/data/runtime/bots/$INSTANCE_ID/stdout.log"
      read -r -p "Enterで閉じます..."
    else
      echo "[OK] bot manager started successfully"
      echo "[INFO] status: $PYTHON_BIN $ROOT_DIR/scripts/bot_manager.py status --all"
      echo "[INFO] logs: tail -f $ROOT_DIR/data/runtime/bots/$INSTANCE_ID/stdout.log"
      read -r -p "Press Enter to close..."
    fi
    exit 0
  fi

  if [[ "$LANG_CODE" == "ja" ]]; then
    echo "[ERROR] Botマネージャ起動失敗 (code=$BOT_RC)"
    read -r -p "Enterで閉じます..."
  else
    echo "[ERROR] bot manager start failed (code=$BOT_RC)"
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
