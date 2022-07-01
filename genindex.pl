#!/usr/local/bin/perl

use strict;
use warnings;
use utf8;
use open ':utf8';
use open ':std';

use DBI;
use File::Basename qw/basename/;
use HTML::TreeBuilder;
use IO::HTML;

#
# HTML::Element のノードからテキストを抽出
#
sub extract_text {
  my ($texts, $element) = @_;

  foreach my $e ($element->content_list()) {
    if (ref $e eq 'HTML::Element') {
      extract_text($texts, $e);
    } else {
      $e =~ s/^\s*//;
      $e =~ s/\s*$//;
      push(@$texts, $e);
    }
  }
}

#
# データベースをオープン
#
my $dbh = DBI->connect('dbi:SQLite:dbname=default.db', '', '',
  { RaiseError => 1, PrintError => 0, sqlite_unicode => 1 }) or die $DBI::errstr;

#
# テーブルがなければ作成
#
$dbh->do(<<'EOS');
CREATE TABLE IF NOT EXISTS records (
  file TEXT PRIMARY KEY, -- ファイルパス
  fsize INTEGER, -- ファイルサイズ（バイト）
  mtime INTEGER, -- 最終修正日時（エポック秒）
  url TEXT,      -- URL
  lang TEXT,     -- 言語
  period TEXT,   -- 開始日
  title TEXT,    -- タイトル
  content TEXT   -- 本文
)
EOS

#
# データベースから検索対象ファイルの最終更新日時を取得
#
my $mtimes = {};
my $sth = $dbh->prepare('SELECT file,mtime FROM records');
$sth->execute();
while (my $row = $sth->fetchrow_hashref) {
  $mtimes->{$row->{file}} = $row->{mtime};
}
$sth->finish;

#
# データベースに検索対象ファイルの情報を登録
#
my $targets = '../[0-9]*.html';       # 🔖 検索対象ファイル
my $baseurl = 'https://anineco.org/'; # 🔖 ベースURL

my $n = 0; # 新規ページ数
my $m = 0; # 更新ページ数
$sth = $dbh->prepare('INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?)');
foreach my $file (glob $targets) {
  my ($fsize, $mtime) = (stat $file)[7, 9];
  if (exists($mtimes->{$file})) {
    next if ($mtimes->{$file} >= $mtime);
    $m++;
  } else {
    $n++;
  }
  
  my $tree = HTML::TreeBuilder->new;
  $tree->ignore_unknown(0); # for 'time' tag
  $tree->parse_file(html_file($file));
  $tree->eof();

  my $url = $baseurl . basename($file); # 🔖 検索対象ファイルのURL
  my $lang = $tree->find('html')->attr('lang');
  my $period = $tree->find('time')->attr('datetime'); # %Y-%m-%d フォーマット
  my $title = $tree->find('title')->as_text();
  my $texts = [];
  extract_text($texts, $tree->find('body'));
  my $content = join(' ', @$texts);
  $tree = $tree->delete;

  $sth->execute($file, $fsize, $mtime, $url, $lang, $period, $title, $content);
  $sth->finish;
}
print '新規ページ数：', $n, "\n";
print '更新ページ数：', $m, "\n";

$dbh->disconnect;
__END__
