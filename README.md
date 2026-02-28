# Q AI Remote

旧称: Q CodeAnzenn。
Telegramで操作する、安全ガバナンス型のローカル作業アシスタントです。

## 配布方針 (日本語優先)
- 配布は GitHub `Public` を推奨
- ライセンスは `MIT`（このリポジトリに `LICENSE` を同梱）
- 初心者向け手順: [docs/manual_beginner_ja.md](docs/manual_beginner_ja.md)
- 紹介文テンプレ: [docs/intro_copy_ja.md](docs/intro_copy_ja.md)
- 脆弱性報告ポリシー: [SECURITY.md](SECURITY.md)

## Contributing
- 参加ガイド: [CONTRIBUTING.md](CONTRIBUTING.md)
- 初心者向けIssue: `Issues` で `good first issue` ラベルを選択
- 改善要望/不具合報告: `Issues > New issue` でテンプレートを選択

### First PR Checklist 📝
Before submitting your first PR, make sure you've completed these steps:

- [ ] Found a `good first issue` or `help wanted` issue and commented to claim it
- [ ] Created a descriptive branch name (e.g., `docs/fix-typo`, `feat/add-feature`)
- [ ] Made your changes following the [Contributing Guide](CONTRIBUTING.md)
- [ ] Ran tests locally: `python -m pytest -q`
- [ ] Kept the PR focused on one purpose
- [ ] Added or updated tests if needed
- [ ] Filled out the PR template completely
- [ ] No secrets, API keys, or sensitive data in your changes

💡 **Tip**: If you're stuck, don't hesitate to ask questions in the Issue. We're here to help!

### 配布用パッケージを自動生成
開発用の `tests/.taskmaster/data` などを除外し、配布に必要なファイルだけを出力します。

```bash
python scripts/export_distribution.py --force
```

出力先（既定）:
- `dist/q-ai-remote-distribution`

### 配布Repoへ自動リリース（export + push）
1コマンドで、配布パッケージ生成から `dist` remote への push まで実行します。

```bash
./.venv/bin/python scripts/release_distribution.py
```

オプション例:
- pushせず確認だけ: `./.venv/bin/python scripts/release_distribution.py --dry-run`
- dirty作業ツリーでも実行: `./.venv/bin/python scripts/release_distribution.py --allow-dirty`

## できること
- Telegramで自由質問（チャット回答）
- `/task` でファイル/コード変更の Plan+Risk 作成
- 承認後のみ実行
- 実行後に `diff + JSONL + HTML` をローカル保存

## クイックセットアップ
ダウンロード後、どちらかを実行します。

- macOS:
  - `scripts/setup_macos.command` をダブルクリック
- Windows:
  - `powershell -ExecutionPolicy Bypass -File scripts\\setup_windows.ps1`

セットアップ完了時:
- 言語を `日本語/English` で選択
- 同一ウィンドウで Bot を自動起動
- 同じ instance が起動中なら自動再起動

## セットアップウィザードが行うこと
- Telegram Bot token を最初に確認
- 必要なら `/start` から `user_id` を自動取得（Bot API `getUpdates`）
- `engine.mode` を設定
- `users.allowlist_user_ids` を設定
- `instance_id` を設定（既定: `default`）
- OS資格情報ストアに秘密情報を保存
  - `telegram_bot_token`（必須）
  - `codex_api_key`（`codex_api` のとき必須）
  - `claude_api_key`（`claude_api` のとき必須）
- サブスクモード時にCLIログイン状態を確認
  - `codex login status`
  - `claude auth status`
- `ui.language` を保存し、Telegramメニュー文言に反映

オプション:
- `QCA_SETUP_AUTOSTART=N` で自動起動をスキップ
- `QCA_SETUP_AUTOSTART_SCOPE=all` で全instance再起動

## 実行方法
1. 依存をインストール
   - `pip install -r requirements.txt`
2. `config/policy.yaml` の `engine.mode` を選択
   - `codex_subscription`
   - `claude_subscription`
   - `codex_api`
   - `claude_api`
3. allowlist を設定
   - `users.allowlist_user_ids`
4. 起動
   - 単体: `python -m src.main --instance-id mybot2`
   - 複数: `python scripts/bot_manager.py start --all`

## Telegramの基本操作
- `/start`: 起動メッセージ
- `/policy`: 現在ポリシー表示
- `/plan <依頼>`: Plan+Risk作成（実行なし）
- `/task <依頼>`: Plan+Risk作成（実行なし）
- `/approve <plan_id> <short_token>`: 承認して実行
- `/reject <plan_id>`: 破棄
- `/status [plan_id]`: 状態確認
- `/logs <plan_id>`: 監査ログ確認

## セキュリティ保証 (MVP)
- `/approve` されるまで実行しない
- 実行可能操作は固定4種のみ
  - `list_dir/read_file/create_file/patch_file`
- Allowed Paths 外アクセスは拒否
- plan所有者以外は `approve/reject/status/logs` を実行不可
- 任意コマンド実行・ネットワーク実行を禁止
- 監査証跡を保存（JSONL hash-chain / HTML / diff）

## マルチボット運用
- Botごとに `instance_id` を分けてセットアップ
- 秘密情報は `qcodeanzenn.<instance_id>` に分離保存
- 一括起動/停止:
  - `python scripts/bot_manager.py start --all`
  - `python scripts/bot_manager.py status --all`
  - `python scripts/bot_manager.py stop --all`

## English (Sub)
- Q AI Remote is a Telegram-operated, safety-governed local execution assistant.
- Use `/task` to generate Plan+Risk, then approve to execute.
- Execution is restricted to fixed safe ops and audited with diff/JSONL/HTML.
- Desktop setup scripts:
  - macOS: `scripts/setup_macos.command`
  - Windows: `scripts/setup_windows.ps1`
