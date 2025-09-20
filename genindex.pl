#!/usr/bin/env perl

use strict;
use warnings;
use utf8;
use open qw(:utf8 :std);

use DBI;
use Encode;
use HTML::TreeBuilder;
use IO::HTML;
use JSON;

my $json = JSON->new->utf8(1);

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
  { RaiseError => 1, PrintError => 0, sqlite_unicode => 1 }
) or die $DBI::errstr;

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
my %mtimes = ();
my $sth = $dbh->prepare('SELECT file,mtime FROM records');
$sth->execute();
while (my $row = $sth->fetchrow_hashref) {
  $mtimes{$row->{file}} = $row->{mtime};
}
$sth->finish;

#
# 存在しないファイルをデータベースから削除
#
my $n_delete = 0; # 削除ページ数
$sth = $dbh->prepare('DELETE FROM records WHERE file=?');
foreach my $file (keys(%mtimes)) {
  next if (-f $file);
  $n_delete++;
  $sth->execute($file);
  $sth->finish;
}

#
# データベースに検索対象ファイルの情報を登録
#
my $basedir = '../';                  # 🔖 検索対象ディレクトリ
my @targets = qw([0-9]*.html);        # 🔖 検索対象ファイル
my $baseurl = 'https://anineco.org/'; # 🔖 ベースURL

my $n_pages = 0;  # 対象ページ数
my $n_insert = 0; # 新規ページ数
my $n_update = 0; # 更新ページ数
$sth = $dbh->prepare('INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?)');
foreach my $file (glob join(' ', map { $basedir . $_ } @targets)) {
  my ($fsize, $mtime) = (stat $file)[7, 9];
  $n_pages++;
  if (exists($mtimes{$file})) {
    next if ($mtimes{$file} >= $mtime);
    $n_update++;
  } else {
    $n_insert++;
  }

  my $tree = HTML::TreeBuilder->new;
  $tree->ignore_unknown(0); # for 'time' tag
  $tree->parse_file(html_file($file));
  $tree->eof();

# JSON-LD から startDate を取得
  my $period;
  my @script_tags = $tree->look_down(_tag => 'script', type => 'application/ld+json');
  for my $script_tag (@script_tags) {
    my $json_text = join(' ', $script_tag->content_list);
    my $data = $json->decode(encode('UTF-8', $json_text));
    if (exists $data->{about} and ref $data->{about} eq 'HASH') {
      if (exists $data->{about}{startDate}) {
        $period = $data->{about}{startDate};
        last;
      }
    }
  }

  my $url = $baseurl . ($file =~ s/^$basedir//r);
  my $lang = $tree->find('html')->attr('lang');
  my $title = $tree->find('title')->as_text();
  my $texts = [];
  extract_text($texts, $tree->find('body'));
  my $content = join(' ', @$texts);
  $tree = $tree->delete;

  $sth->execute($file, $fsize, $mtime, $url, $lang, $period, $title, $content);
  $sth->finish;
}
print '削除ページ数：', $n_delete, "\n";
print '新規ページ数：', $n_insert, "\n";
print '更新ページ数：', $n_update, "\n";
print '対象ページ数：', $n_pages, "\n";

$dbh->disconnect;
__END__
