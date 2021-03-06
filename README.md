# サイト内全文検索 SQLite3 版 msearch
Katsushi Matsuda氏、毛流麦花氏が開発された [Unicode 版 msearch 1.52(U5)](https://www.marbacka.net/msearch/) を SQLite3 を利用してリファクタリング。msearch 1.52(U5) の機能を全て実現したものではないので、注意。
## msearch 1.52(U5) からの主な変更点
* Perl ソースコードの文字コードを EUC-JP から UTF-8 に変更。 
* HTML ファイルの解析に HTML::TreeBuilder を利用。検索対象の HTML ファイルの文字コードは、Shift_JIS、EUC-JP、UTF-8 のいずれにも対応。 
* インデックスファイルとして、SQLite3 のデータベースファイルを利用。全文検索では、msearch 1.52(U5) と同等の検索式が利用できる。検索式を SQL の WHERE 句の条件式に変換して、全文検索を実行する。 ただし、全文検索と言っても、INSTR 関数で部分一致検索を行っているだけである。
* 検索結果は HTML Living Standard、文字コードを UTF-8 として出力する。レスポンシブデザインにより、PC とモバイルでの表示に対応。検索結果の表示はページに分割せず、ページの一部をスクロールして表示する。 
* 出力する HTML ファイルのテンプレートは、Perl ソースコードのヒアドキュメントに記述。 
* 構成ファイルは genindex.pl、msearch.cgi、msearch.css の３つ。
* SQLite3 と CPAN モジュールを活用したことにより、構成ファイルの行数の合計は約650行と極めてコンパクト。ちなみに msearch 1.52(U5) は msearch.cgi だけで約2,100行ある。 
## 利用例
あにねこ登山日誌 [HP内検索ページ](https://anineco.org/msearch/msearch.cgi)
## 設置方法
* genindex.pl の「# 🔖」が付された行を、設置するサイトに合わせて変更。
* msearch.cgi についても「# 🔖」が付された行を必要に応じて変更。 
* 必要に応じて、シバン（1行目の #!/usr/local/bin/perl）のパスを変更。
* ローカル環境にて genindex.pl でデータベースファイル（ファイル名：default.db）を作成する。
* ウェブサーバには msearch.{cgi,css}、nek9c.jpg（背景画像ファイル）と作成した default.db を設置する。 
