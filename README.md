# 決済業務のn8nテンプレート

入金・請求・通知などの定型作業をn8nでつなぐ、業務自動化テンプレートの開発リポジトリです。
現時点で実装と導入資料が揃っているのは **テンプレート01「入金消込」** です。計画中の4本すべてが完成しているわけではありません。

## 現在の状態

| テンプレート | リポジトリにあるもの | 状態 |
| --- | --- | --- |
| 01 入金消込 | 本体・エラー処理のworkflow JSON、Codeノード原本、日英の導入資料、架空サンプル、検証記録 | 実装済み。Google / Slack等のライブ接続検証は残項目あり |
| 03 未入金リマインド | 設計とfixtureの下書き | 未レビュー・実装未着手 |
| 02 決済Webhook → 会計 | 共通仕様内の計画 | 未着手 |
| 04 返金・チャージバック管理 | 共通仕様内の計画 | 未着手 |

工程・残項目の記録は [PROGRESS.md](PROGRESS.md) と [BLOCKERS.md](BLOCKERS.md) を参照してください。

## 入金消込でできること

- 銀行CSV・入金通知メールから入金情報を取り込み、名義・金額を正規化する。
- Google Sheetsの請求一覧と突き合わせ、消込済み・要確認・候補複数・未消込を整理する。
- 再実行時の重複処理を防ぎ、未消込の定期再突合と設定したチャネルへの通知を行う。
- 特定銀行のCSV形式に固定せず、列対応とメール抽出ルールを設定する。

金額一致だけ・手数料差引・合算による一致も、一部は自動確定したうえで「要確認」に通知する設計です。候補複数などの未確定結果と混同しないよう、[判定規則](templates/01-bank-reconciliation/README.ja.md) を確認してください。会計ソフトへの記帳や税務判断は行いません。

## 試す・導入する

1. [日本語の製品説明](templates/01-bank-reconciliation/README.ja.md) で入力・判定規則・制限を確認する。
2. [日本語セットアップ](templates/01-bank-reconciliation/SETUP.ja.md) に従って、n8nへ本体とError Workflowを取り込む。
3. 架空サンプルと専用シートで設定・試験する。実アカウントに接続する場合は、自分のCredentialをn8nへ登録する。
4. Google系・通知先のライブ確認が必要な項目を [BLOCKERS.md](BLOCKERS.md) と照合する。

n8n 2.40.5のセルフホスト環境で構築された記録があります。n8n Cloudや別バージョンでの動作保証ではありません。
開発用の [infra/docker-compose.yml](infra/docker-compose.yml) はイメージを特定バージョンへ固定していないため、検証記録と同一版が必要な場合は実行環境を合わせてください。

## 実装・検証資料

- [workflow.json](templates/01-bank-reconciliation/workflow.json) / [error-handler.json](templates/01-bank-reconciliation/error-handler.json)
- [Codeノードの原本](templates/01-bank-reconciliation/code) / [生成スクリプト](templates/01-bank-reconciliation/build/build_workflow.py)
- [設計](templates/01-bank-reconciliation/DESIGN.md) / [検証結果](templates/01-bank-reconciliation/tests/RESULTS.md)
- [単体・結合の確認スクリプト](templates/01-bank-reconciliation/tests/unit/run-all.sh) / [架空データ](templates/01-bank-reconciliation/fixtures)
- [共通シート構造](shared/sheets-schema.md)

生成物とソースの一致を確認するには、Python 3系で次を実行します。

```sh
python templates/01-bank-reconciliation/build/build_workflow.py --check
```

単体試験はテンプレート01のフォルダー内で `bash tests/unit/run-all.sh` を使います。Node.js・Python・シェル等、スクリプトが必要とする環境を用意してください。既存の検証にはpinned dataやローカル通知先による代替があり、Google / Slackへの実接続完了を意味しません。

## 制作・利用条件

制作・管理：**Atsushi Odajima**。実装・資料作成にはAI支援を利用しています。
テンプレート01の利用条件は [LICENSE.md](templates/01-bank-reconciliation/LICENSE.md) を参照してください。ソース閲覧と、再販売・再配布の許可は別です。
