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
# データベースを新規に作成する
#
unlink 'default.db';
my $dbh = DBI->connect('dbi:SQLite:dbname=default.db', '', '',
  { RaiseError => 1, PrintError => 0, sqlite_unicode => 1 });

$dbh->do(<<'EOS');
CREATE TABLE records (  -- 山行記録
  file TEXT,            -- ファイルパス
  fsize INTEGER,        -- ファイルサイズ（バイト）
  mtime INTEGER,        -- 最終修正日時（エポック秒）
  url TEXT PRIMARY KEY, -- URL
  lang TEXT,            -- 言語
  period TEXT,          -- 開始日
  title TEXT,           -- タイトル
  content TEXT          -- 本文
)
EOS

#
# データベースにデータを登録
#
my $targets = '../[0-9]*.html';       # 🔖 NOTE: 検索対象ファイル
my $baseurl = 'https://anineco.org/'; # 🔖 NOTE: ベースURL

my $sth = $dbh->prepare('INSERT INTO records VALUES (?,?,?,?,?,?,?,?)');
my $m = 0;
foreach my $file (glob $targets) {
  my ($fsize, $mtime) = (stat $file)[7, 9];

  my $tree = HTML::TreeBuilder->new;
  $tree->ignore_unknown(0); # for 'time' tag
  $tree->parse_file(html_file($file));
  $tree->eof();

  my $url = $baseurl . basename($file); # 🔖 NOTE: 検索対象ファイルのURL
  my $lang = $tree->find('html')->attr('lang');
  my $period = $tree->find('time')->attr('datetime'); # %Y-%m-%d フォーマット
  my $title = $tree->find('title')->as_text();
  my $texts = [];
  extract_text($texts, $tree->find('body'));
  my $content = join(' ', @$texts);
  $tree = $tree->delete;

  $sth->execute($file, $fsize, $mtime, $url, $lang, $period, $title, $content);
  $sth->finish;
  $m++;
}
print 'ページ数：', $m, "\n";

$dbh->disconnect;
__END__
