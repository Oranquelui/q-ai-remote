# Contributing to Q AI Remote

初心者歓迎です。小さな修正から始めれば十分です。

## Why This Guide Exists
- 何をすればよいか分からない問題を減らす
- 初回PRの不安を減らす
- レビュー待ち時間のストレスを減らす

## First Contribution Flow
1. `Issues` から `good first issue` または `help wanted` を選ぶ
2. 「担当したい」とコメントする
3. ブランチを作る（例: `docs/fix-typo`）
4. 修正してテストを実行
5. Pull Request を作成（テンプレートに沿って記入）

## Local Setup
macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python3 -m pytest -q
```

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

## What To Work On First
- ドキュメント改善（誤字、説明不足、手順追加）
- テスト追加（回帰テスト、境界値）
- 小さなUX改善（メッセージ文言、導線）

## Pull Request Rule Of Thumb
- 1PR = 1目的
- 変更理由をPR本文に書く
- 変更に対応するテストを追加、または既存テストが通ることを示す
- 破壊的変更は明記する

## Review Policy
- 初回返信目標: 48時間以内
- 指摘対応が必要な場合は、再レビュー前に対応内容を簡潔にコメントする

## Security
- 秘密情報（APIキー、トークン）をコミットしない
- 脆弱性報告は公開Issueではなく [SECURITY.md](SECURITY.md) に従う

## Need Help?
- Issue で質問してOKです
- 日本語 / English どちらでもOKです

