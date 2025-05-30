# 現状の課題と改善方針

## 優先度の高い課題

1. **[テスト] テスト網羅性の向上**
   - 課題: テストケースのカバレッジを向上させる必要がある
   - 改善方針: 境界値テストやエラーケーステストを追加する
   - 関連MDC: `python_test.mdc`
   - ステータス: 未着手
   - 更新日: 2023-12-01

2. **[ドキュメント] ドキュメント整備**
   - 課題: 使用方法や内部設計に関するドキュメントが不足している
   - 改善方針: READMEの拡充とAPIドキュメントの整備
   - 関連MDC: `phases/document.mdc`
   - ステータス: 進行中
   - 更新日: 2023-12-10

3. **[MDC] MDCルールとコードベースの整合性**
   - 課題: MDCに記載されているルールと実際のコードベースに不整合がある
   - 改善方針: 以下の不整合を解消する
     - `green.mdc`で指定されている`result`型を使用したエラー処理が一部のコードで実装されていない
     - テスト構造が`python_test.mdc`で指定された構造と完全に一致していない
   - 関連MDC: `phases/green.mdc`, `python_test.mdc`
   - ステータス: 未着手
   - 更新日: 2023-12-15

4. **[PowerShell] PowerShellコマンド実行の互換性問題**
   - 課題: PowerShell環境でのパス処理やコマンド構文に関する互換性問題が存在する
   - 改善方針: 以下の問題に対処する
     - 長いパス名や複雑なパス名を含むコマンドでのバッファオーバーフロー
     - Unix/Linux系コマンド構文とPowerShellコマンドレットの構文の違いによるエラー
     - 複数ファイルの一括処理をクロスプラットフォームで動作させるためのスクリプト改善
   - 関連MDC: `environment.mdc`
   - ステータス: 進行中
   - 更新日: 2023-12-20

5. **[型チェック] 型チェッカーのエラー解消**
   - 課題: mypyによる型チェックで多くのエラーが検出されている
   - 改善方針: 以下の問題を修正する
     - クラス構造の変更に伴うインターフェース不整合（特にPowerShellControllerSettings）
     - 変数の再定義エラー（same name used for multiple variables）
     - 戻り値の型エラー（Returning Any from function declared to return specific type）
     - 到達不能コード（Statement is unreachable）
     - 抽象クラスの実装漏れ（abstract attributes not implemented）
   - 関連MDC: なし
   - ステータス: 未着手
   - 更新日: 2024-01-05

6. **[PowerShell] PSReadLineモジュールのバグ対応**
   - 課題: コマンド実行時にPSReadLineモジュールのバグによりArgumentOutOfRangeExceptionが発生する
   - 改善方針: 以下の対策を実施する
     - 長いコマンドを複数の短いコマンドに分割して実行する
     - コマンド実行前にバッファサイズを確認・調整する処理を追加
     - PSReadLineモジュールのバージョン互換性を確認し、安定バージョンを使用するよう推奨する
     - コマンド実行時の代替手段（スクリプトファイル経由での実行など）を提供する
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 進行中
   - 更新日: 2024-01-10

7. **[ドキュメント] ツール制限の文書化と回避策の提供**
   - 課題: 開発に使用されるツールの制限が文書化されておらず、回避策が共有されていない
   - 改善方針: 以下の対策を実施する
     - ツールの制限に関するMDCファイル（tool_constraints.mdc）を作成・維持する
     - 制限を発見した場合の報告フローを確立する
     - 既知の制限に対する回避策を具体的なコード例とともに提供する
     - 新しいツールや機能を導入する際に既知の制限をテストする仕組みを整備する
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 完了
   - 更新日: 2024-01-20

8. **[環境] 一時ファイル管理の方針整備**
   - 課題: テストや検証で作成した一時ファイルが削除されずに残っている
   - 改善方針: 以下の対策を実施する
     - 一時ファイル管理に関するルールを適切なMDCに記載する
     - テスト・検証完了後の自動クリーンアップ手順を確立する
     - 一時ファイルの命名規則と保持期間のポリシーを定める
     - 使用目的に応じた一時ファイルの管理方法を整理する
   - 関連MDC: `environment.mdc`
   - ステータス: 未着手
   - 更新日: 2024-02-01

9. **[MDC] MDC構造の最適化と記載場所選定ガイドラインの作成**
   - 課題: MDCファイル間の責任分担が曖昧で、新規情報の追加時に適切な記載場所を選定しづらい
   - 改善方針: 以下の対策を実施する
     - MDCファイル間の明確な責任分担を定義する
     - 情報の種類・目的に応じた適切な記載場所を決定するためのフローチャートを作成する
     - MDC構造の全体像を視覚化したドキュメントを整備する
     - 新しい課題やルールを追加する際の標準的な手順を確立する
   - 関連MDC: `docs/mdc_metamodel.mdc`, `MDC_structure_guidelines.md`
   - ステータス: 完了
   - 更新日: 2024-02-15

10. **[MDC] 空フォルダの管理とクリーンアップルールの確立**
    - 課題: 構造変更時に不要な空フォルダが残り、MDC構造が不明瞭になる
    - 改善方針: 以下の対策を実施する
      - 空フォルダの取り扱い原則を明確に定義する
      - リファクタリング時の不要フォルダ削除手順を確立する
      - 空フォルダチェック手順をMDC更新作業に組み込む
      - 一時フォルダの命名規則と管理ルールを定める
    - 関連MDC: `MDC_structure_guidelines.md`
    - ステータス: 完了
    - 更新日: 2024-06-05

11. **[MDC] MDCの意味の統一**
    - 課題: MDCの意味が「Model-Driven Coding」と「Markdown Cursor」で混在していた
    - 改善方針: 以下の対策を実施する
      - 全てのMDCファイルで「Markdown Cursor」に統一する
      - 主要なMDCファイルに「MDCについて」セクションを追加して明確に説明する
      - READMEにもMDCの意味を正確に記載する
      - 今後の新規MDCファイル作成時のテンプレートにMDC説明を含める
    - 関連MDC: 全MDCファイル
    - ステータス: 進行中
    - 更新日: 2024-02-20

12. **[MDC] MDCルール遵守の強化メカニズム**
    - 課題: MDCに記載されたルールが遵守されない場合がある
    - 改善方針: 以下の対策を実施する
      - 各MDCファイルの冒頭に「このMDCは必ず遵守すべき」という注意書きを追加
      - 主要なルールをチェックリスト形式で提供し、作業開始前に確認させる
      - ルール違反を検出するための自動チェックスクリプトの作成（例：命名規則チェック）
      - 違反が発見された場合の報告・修正プロセスを明確化
      - 特に重要なルールには「重要度:高」などの明示的なマーキングを追加
    - 関連MDC: `flows/main/mdc_check.mdc`
    - ステータス: 未着手
    - 更新日: 2024-03-01

13. **[ツール] MDC参照・修正支援ツールの開発**
    - 課題: MDCファイルを修正する際に適切なファイルを選択できない場合がある
    - 改善方針: 以下の対策を実施する
      - インタラクティブなMDC選択ガイドの作成（「どのような情報を追加/修正したいですか？」から適切なMDCを案内）
      - MDCファイル間の関係を視覚化した参照図の作成と定期的な更新
      - 各MDCファイルに「修正時の注意点」セクションを追加
      - MDC構造のREADMEを.cursor/rulesのルートに配置して参照しやすくする
      - 全MDCファイルに統一されたヘッダー形式を導入し、責任範囲を明記
    - 関連MDC: `MDC_structure_guidelines.md`
    - ステータス: 未着手
    - 更新日: 2024-03-10

14. **[自動化] MDC更新検証フローの自動化**
    - 課題: MDCファイル更新後の検証が手動で行われており、不整合が見逃される場合がある
    - 改善方針: 以下の対策を実施する
      - MDC間の相互参照リンクの有効性を自動チェックするスクリプトの作成
      - 更新されたMDCファイルの整合性を検証するためのレビューチェックリストの作成
      - 主要なMDCファイル更新時に関連ファイルも更新すべきかを確認するプロンプトの追加
      - MDC更新履歴を記録し、変更内容を追跡できるようにする
      - 定期的なMDC整合性確認フローの実行スケジュールの設定
    - 関連MDC: `flows/main/mdc_check.mdc`
    - ステータス: 未着手
    - 更新日: 2024-03-20

15. **[命名規則] MDCファイル命名規則とパス指定の標準化**
    - 課題: MDCファイル間の参照パスが統一されておらず、リンク切れが発生しやすい
    - 改善方針: 以下の対策を実施する
      - 全てのMDCファイルで一貫した相対パス指定方法に統一
      - MDCファイル命名規則の明確化（カテゴリ_サブカテゴリ_name.mdcなど）
      - 頻繁に参照されるMDCファイルはshortcut links（エイリアス）を定義して参照を簡素化
      - パス指定エラーを検出するためのリンクチェッカーの導入
      - ファイル移動時の参照パス一括更新スクリプトの開発
    - 関連MDC: `MDC_structure_guidelines.md`
    - ステータス: 未着手
    - 更新日: 2024-04-01

16. **[プロセス] MDCルール遵守の即時性確保**
    - 課題: 新たな問題（PSReadLineエラーなど）が発生してもMDCに即時反映されていない
    - 改善方針: 以下の対策を実施する
      - 「即時ドキュメント化ワークフロー」の導入：エラー発生時に即時にissues.mdに記録するプロセス
      - エラー発生時のチェックリスト作成：エラーの性質、発生環境、対策案の記録手順
      - 緊急課題フラグの導入：即時対応が必要な課題を識別するためのマーキング
      - エラー記録→分析→ドキュメント化の一連フローを標準化
      - 「問題発生→ドキュメント化」までの目標時間（24時間以内）の設定
    - 関連MDC: `docs/tool_constraints.mdc`, `MDC_structure_guidelines.md`
    - ステータス: 未着手
    - 更新日: 2024-06-05

17. **[文化] MDC遵守文化の強化**
    - 課題: MDCルールの存在を認識していても実践されない場合がある
    - 改善方針: 以下の対策を実施する
      - 「MDC First」原則の確立：問題解決前の課題記録を義務化
      - チェックポイントの追加：作業完了時に「MDC更新したか？」の確認手順
      - 事後レビュープロセスの確立：作業後24時間以内にMDC遵守状況を確認
      - MDC違反の分析と傾向把握：同じパターンの違反が繰り返されていないか分析
      - 緊急時のショートカットプロセス：最小限の記録で即時対応後、詳細を追記
    - 関連MDC: `docs/main.mdc`
    - ステータス: 未着手
    - 更新日: 2024-06-05

18. **[MDC] MDC参照インデックスの導入と運用**
    - 課題: 問題発生時や情報追加時に適切なMDCを即座に特定し参照することが困難
    - 改善方針: 以下の対策を実施する
      - 問題タイプ・状況別にMDC参照先を明示したインデックスを作成
      - 緊急時の最小記録テンプレートを用意
      - 問題記録→MDC更新の標準フローを確立
      - インデックスの定期的な更新・メンテナンス体制の構築
      - 既存MDC参照の効率化（RAILのような構造化参照の良い部分を応用）
    - 関連MDC: `mdc_reference_index.mdc`, `MDC_structure_guidelines.md`
    - ステータス: 完了
    - 更新日: 2024-06-05

19. **[プロセス] 自動エラー記録メカニズムの確立**
    - 課題: エラー発生時の即時ドキュメント化が一貫して行われない
    - 改善方針: 以下の対策を実施する
      - PowerShellスクリプトによる自動エラー記録機能の実装
      - エラー発生時のワンクリック記録メカニズムの導入
      - PowerShellプロファイルへのショートカット関数追加
      - 記録後の視覚的フィードバック（色付きメッセージなど）提供
      - 一時記録と永続記録の自動連携プロセス確立
    - 関連MDC: `mdc_reference_index.mdc`, `docs/tool_constraints.mdc`
    - ステータス: 進行中
    - 更新日: 2024-06-05

20. **[MDC] MDCファーストアプローチの導入**
    - 課題: 開発プロセスとMDC管理を統合するMDCファーストアプローチを導入
    - 実装内容: 
      - PowerShellスクリプトによるMDC管理の自動化
      - エラー発生時の即時記録メカニズム
      - 作業開始時のMDC起点プロセス確立
      - プロンプトへの作業状態表示統合
      - 課題状態のコマンドライン更新機能
    - 導入ファイル:
      - `scripts/mdc_first_approach.ps1`: メインスクリプト
      - `scripts/install_mdc_first.ps1`: インストーラー
      - `scripts/quick_start.ps1`: クイックスタートスクリプト
      - `scripts/README.md`: ドキュメント
    - 関連MDC: `mdc_reference_index.mdc`
    - ステータス: 完了
    - 更新日: 2024-06-06

## ユーザー対応の課題
（現在記載なし）

## 環境依存の問題

1. **[PowerShell] PowerShell 7のPSReadLineモジュールバグ**
   - 問題: Windows環境でのコマンド実行時にPSReadLineモジュールでArgumentOutOfRangeExceptionが発生
   - 発生環境: Windows 10.0.26100, PowerShell 7.5.1, PSReadLine 2.3.6
   - エラーメッセージ: `System.ArgumentOutOfRangeException: The value must be greater than or equal to zero and less than the console's buffer size in that dimension.`
   - 推定原因: コンソールのバッファサイズを超える操作やバッファ位置の計算ミスがPSReadLineモジュールで発生
   - 解決策:
     - 長いコマンドを分割して実行する
     - スクリプトファイルを使用してコマンドを実行する
     - PSReadLineモジュールの更新またはダウングレードを検討する
     - コマンド実行用のラッパー関数を作成し、エラーハンドリングを追加する
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 未解決
   - 更新日: 2024-06-05

2. **[PowerShell] 複雑なコマンド実行時のPSReadLineバグ再現性**
   - 問題: 引用符を含む複雑なパス指定や長いコマンドを実行する際に、PSReadLineモジュールで例外が頻発する
   - 発生環境: Windows 10.0.26100, PowerShell 7, フォルダ削除コマンド実行時
   - エラーメッセージ: `System.InvalidOperationException: Cannot locate the offset in the rendered text that was pointed by the original cursor.`
   - 推定原因: PSReadLineのバッファ管理機能がコマンドラインの複雑な状態を適切に処理できない
   - 解決策:
     - Remove-Itemなど標準PowerShellコマンドレットのみを使用する
     - 単純なパス指定で複数回に分けて実行する
     - スクリプトファイルに処理を分離する
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 未解決
   - 更新日: 2024-06-05

3. **[ツール] run_terminal_cmdツールの制限**
   - 問題: コマンド引数に改行文字を含めることができない
   - 発生環境: すべての環境（ツール自体の制限）
   - エラーメッセージ: `Tool call arguments for run_terminal_cmd were invalid: Argument command must not contain newline characters.`
   - 推定原因: ツールの設計上の制限
   - 解決策:
     - ヒアドキュメント（`@'...'@`）を使用する代わりに、`edit_file`ツールでスクリプトを作成してから実行する
     - 複数行のコマンドを一行に結合して実行する
     - 複雑なコマンドはスクリプトファイルに分離する習慣をつける
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 回避策あり
   - 更新日: 2024-01-20

4. **[PowerShell] UNIXスタイルコマンドの互換性問題**
   - 問題: UNIXスタイルのコマンド（rm -rf など）がPowerShellで直接使用できない
   - 発生環境: Windows 10.0.26100, PowerShell 7
   - エラーメッセージ: `Remove-Item: A parameter cannot be found that matches parameter name 'rf'.`
   - 推定原因: PowerShellはBashなどのUNIXシェルとは異なる構文を持つ
   - 解決策:
     - PowerShellネイティブコマンドレットを使用する（例: `Remove-Item -Path "ファイル名" -Force -Recurse`）
     - エイリアスを作成する（例: `Set-Alias -Name rm -Value Remove-Item`）
     - PowerShell実行前にコマンド変換を行う
   - 関連MDC: `docs/tool_constraints.mdc`
   - ステータス: 回避策あり
   - 更新日: 2024-06-05

## 補足事項

- PowerShell 7の環境依存性への対応は継続的に監視し、新しい問題が発見された場合はすぐに報告してください
- パフォーマンス最適化（大量のコマンド実行時）は次期リリースでの重点課題として検討中です
- セキュリティ強化（入力検証の徹底）については、すべての新規コードで入力検証を徹底することを推奨します
- MDCルール違反の根本原因：「即時性優先による記録後回し」「エラー記録の重要性認識不足」「慣れによる手順スキップ」が主な要因
- MDC遵守のための原則：「先にドキュメント、後に実装」「エラーは発見次第すぐに記録」「問題解決はissues.mdから始める」