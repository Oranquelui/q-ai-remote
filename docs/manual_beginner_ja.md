# Q AI Remote 初心者マニュアル (macOS)

このマニュアルは「初めてGitHubから落として、Telegramで動かす」人向けです。

## 1. 先に知っておくこと
- このツールは Telegram を操作画面として使います。
- ファイル変更は `Plan -> 承認 -> 実行` の順です。
- 実行できる操作は安全な4種類のみです:
  - `list_dir`
  - `read_file`
  - `create_file`
  - `patch_file`

## 2. 事前準備
1. Telegram アプリを入れる。
2. BotFather でBotを1つ作る。
3. BotFather が出す `token` を控える。
4. Terminal が使える状態にする（macOS標準で可）。

## 3. インストールと初期設定
1. このリポジトリをダウンロードして開く。
2. Finder で `scripts/setup_macos.command` をダブルクリック。
3. 画面で順番に入力:
   - 言語: `日本語` または `English`
   - セットアップ種別: 初回なら `1`
   - `instance_id`: 例 `default`（英数 / `_` / `-` のみ）
   - Telegram Botトークン
   - engine mode（通常は `codex_subscription` か `claude_subscription`）
   - allowlist user id（自分のTelegram user id）
4. 完了後、Botが自動起動します。

## 4. Telegramで最初にやること
1. 作ったBotチャットを開く。
2. `/start` を送信。
3. 返答が来れば接続OK。

## 5. 基本操作 (最短)
1. `新規TASK` ボタンを押す。
2. 1メッセージで依頼を書く。
3. Botが `plan_id` と `short_token` を返す。
4. `✅ 実行` ボタンを押す。
5. `status: 完了 (EXECUTED)` が出れば成功。

## 6. そのまま使える入力例
### 6-1. 新規LPを作る
```text
/task docs/lp_demo/index.html と docs/lp_demo/styles.css を新規作成。スマホ最適の観光LPを作成。
```

### 6-2. 既存LPを更新する
```text
/task docs/lp_demo/index.html と docs/lp_demo/styles.css を更新。create_fileは使わず patch_file で修正。
```

## 7. 作成したLPを確認する
### 7-1. Macブラウザで確認
```bash
cd /Users/louistoyozaki/Documents/GitHub/QCodeAnzenn/docs/lp_demo
python3 -m http.server 8000 --bind 127.0.0.1
```
ブラウザで `http://127.0.0.1:8000/index.html` を開く。

### 7-2. 同じWi-Fiのスマホで確認
```bash
ipconfig getifaddr en0
```
表示されたIPを `A.B.C.D` とすると、スマホで `http://A.B.C.D:8000/index.html` を開く。

## 8. よくあるエラーと対処
### 8-1. `Invalid token`
- BotFatherトークンが違うか、保存先サービスが違います。
- setupを再実行してトークンを入れ直してください。

### 8-2. `localhost refused to connect`
- `http.server` が起動していません。
- もう一度 `python3 -m http.server 8000 --bind 127.0.0.1` を実行してください。

### 8-3. `create_file target already exists`
- 既存ファイルに `create_file` を当てています。
- 次は `patch_file` 指定で依頼してください。

### 8-4. `/logs` で何も出ない
- 実行前のPlanはログ対象外です。
- 実行後の `plan_id` を指定して `/logs <plan_id>` を使ってください。

## 9. 配布時の推奨設定
1. GitHub repository visibility を `Public` にする。
2. LICENSE を `MIT` にする。
3. README先頭に次を明記:
   - 対応OS
   - セットアップ方法
   - セキュリティ制約
   - トラブルシュート

## 10. このツールの安全設計
- 承認前実行なし
- Allowed Paths外拒否
- 任意コマンド禁止
- 実行後の監査ログ（JSONL / HTML / diff）保存

