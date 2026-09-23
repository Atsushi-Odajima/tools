# ライセンス / License — [Odaji] 01 Bank Deposit Reconciliation

## JA

本テンプレート（`workflow.json`、`error-handler.json`、`code/`、`shared/`、`fixtures/`、ドキュメント一式。以下「本製品」）は、購入者である **1 事業者**（個人事業主 1 名、または 1 法人）が自らの業務のために利用することを許諾する「単一事業者ライセンス」で提供されます。

### 許諾されること
1. 購入者自身の n8n 環境（自社サーバー、n8n Cloud のいずれも可。台数・インスタンス数の制限なし）に本製品を導入し、業務に使用すること。
2. 購入者の業務に合わせて本製品を自由に改変すること（ノードの追加・削除、文面や Config の変更、Code ノードの修正を含む）。
3. 購入者の従業員・業務委託先が、購入者の業務のためにのみ本製品を操作すること。

### 禁止されること
1. 本製品または改変物を、再販・再配布・転売・貸与・公開すること（無償を含む）。
2. 本製品または改変物を、他のテンプレート製品・有料コンテンツ・受託納品物の一部として第三者に提供すること（顧客ごとに本製品を購入すれば可）。
3. 本製品の同梱ドキュメント・文面・付箋の内容を、別製品の販売物として転用すること。

### 保証と責任
- 本製品は現状有姿で提供されます。銀行 CSV や入金通知メールの形式は金融機関ごとに異なり、すべての形式との互換を保証しません。
- 本製品の使用により生じた損害（消込の誤り、通知の不達、外部サービスの課金を含む）について、作者は責任を負いません。本番運用の前に、同梱の fixtures と試運転手順（SETUP.ja.md §7）で必ず確認してください。
- 会計・税務上の取扱いについて本製品は判断しません。必要に応じて税理士等の専門家に確認してください。

### サポート
- 購入日から 30 日間、メールでの導入サポート（SETUP どおりに導入できない場合の質問対応）を提供します。改変後の動作、金融機関固有の形式対応、n8n 自体の不具合はサポート対象外です。

### その他
- n8n は n8n GmbH の製品であり、本製品は n8n 公式・関連会社の製品ではありません。
- 本ライセンス文は法的助言ではありません。契約上の疑義がある場合は専門家に確認してください。

## EN

This template (`workflow.json`, `error-handler.json`, `code/`, `shared/`, `fixtures/` and the bundled documentation; the "Product") is licensed under a **single-business license** to the purchaser: one sole proprietor or one legal entity, for its own business use.

### You may
1. Install and run the Product in any n8n environment you operate (self-hosted or n8n Cloud, any number of instances) for your own business.
2. Modify the Product freely for your own use (add or remove nodes, change copy and Config, edit the Code nodes).
3. Let your employees and contractors operate the Product, solely for your business.

### You may not
1. Resell, redistribute, sublicense, lend or publish the Product or any derivative, whether or not for a fee.
2. Include the Product or a derivative in another template product, paid content or client deliverable (buy one license per client instead).
3. Reuse the bundled documentation, copy or sticky-note text as part of another product for sale.

### Warranty and liability
- The Product is provided as is. Bank CSV layouts and deposit-notification emails differ between institutions; compatibility with any specific bank is not guaranteed.
- The author is not liable for damages arising from use of the Product, including reconciliation errors, undelivered notifications or third-party service charges. Test with the bundled fixtures and the trial-run procedure (SETUP.en.md §7) before production use.
- The Product makes no accounting or tax determinations. Consult a qualified professional where needed.

### Support
- Email installation support for 30 days from the purchase date (questions about deploying as described in SETUP). Modified workflows, institution-specific formats and defects in n8n itself are out of scope.

### Other
- n8n is a product of n8n GmbH. The Product is not affiliated with or endorsed by n8n.
- This license text is not legal advice.
