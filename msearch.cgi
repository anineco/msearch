#!/usr/local/bin/perl

use strict;
use warnings;
use utf8;
use open ':utf8';
use open ':std';

use CGI;
use CGI::Carp qw/fatalsToBrowser/;
use DBI;
use POSIX qw/strftime/;

#
# HTML特殊文字をエスケープ
#
sub htmlspecialchars {
  my $s = shift;
  $s =~ s/&/&amp;/g;
  $s =~ s/</&lt;/g;
  $s =~ s/>/&gt;/g;
  $s =~ s/"/&quot;/g;
  $s =~ s/'/&apos;/g;
  return $s;
}

#
# HTMLヘッダー部出力（共通）
#
sub print_head {
  my ($title, $query) = @_;
  my $help = length($query) ? '<a href="msearch.cgi">HELP</a>' : '';
  $title = htmlspecialchars($title);
  $query = htmlspecialchars($query);

  print <<"EOS";
Content-type: text/html;charset=UTF-8

<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>$title</title>
<link rel="stylesheet" href="msearch.css">
</head>
<body>
<div id="container">
<header>
<form action="msearch.cgi" method="GET" accept-charset="UTF-8">
<table>
<tr>
<td>
<a href="..">TOP</a><!-- 🔖 TOPページへのリンク -->
$help
</td>
<td class="powerd">Powered by msearch</td>
</tr>
<tr>
<td colspan="2">
<input type="text" size="30" name="query" value="$query">
<input type="submit" value="HP内検索">
</td>
</tr>
</table>
</form>
EOS
}

#
# HTMLステータス出力
#
sub print_status {
  my ($s1, $s2) = @_;

  print <<"EOS";
<table class="status">
<tr>
<td>$s1</td>
<td>$s2</td>
</tr>
</table>
</header>
<main>
<article>
EOS
}

#
# HTMLヘルプ出力
#
sub print_help {
  print <<'EOS';
<h2>SQLite3 版 msearch による検索方法</h2>
<table class="example">
<tr>
<th>例</th>
<th>意味</th>
</tr>
<tr>
<td>AAA</td>
<td>キーワード「AAA」を含むページを検索。</td>
</tr>
<tr>
<td>AAA BBB</td>
<td>キーワード「AAA」と「BBB」を両方とも含むページを検索。</td>
</tr>
<tr>
<td>-AAA</td>
<td>キーワード「AAA」を含まないページを検索。</td>
</tr>
<tr>
<td>(AAA BBB)</td>
<td>キーワード「AAA」と「BBB」の少なくとも一方を含むページを検索。(AAA BBB CCC)のように2つ以上のキーワードでもOKです。ただし、ネストはできません。</td>
</tr>
<tr>
<td>t:AAA</td>
<td>キーワード「AAA」がページのタイトルに含まれるページを検索。</td>
</tr>
<tr>
<td>u:AAA</td>
<td>キーワード「AAA」をページのURLに含むページを検索。</td>
</tr>
</table>
<table class="desc">
<tr>
<td>(1)</td>
<td>キーワード間は半角スペース、または、全角スペースで区切って下さい。</td>
</tr>
<tr>
<td>(2)</td>
<td>半角英数文字と全角英数文字、英文字の大文字と小文字は区別して検索します。</td>
</tr>
<tr>
<td>(3)</td>
<td>上の条件式を組み合わせて検索式を作ることができます。例えば、「A B (C D) (E F G) -H t:I u:J」等の複雑な検索式も可能です。この検索式の意味は、『AとBを含み、かつCかDを含み、かつEかFかGを含み、かつHを含まず、かつタイトルにIを含み、かつURLにJを含む』となります。</td>
</tr>
<tr>
<td>(4)</td>
<td>「-1」のようなマイナスから始まる文字列を検索したい場合は、「"-1"」のように半角のダブルクオーテーション(")で囲って下さい。さもないと「1」を含まないというNOT検索になってしまいます。ただし、OR検索内ではダブルクオーテーションは必要ありません。(例：「(-1 -2)」で-1か-2を含むというOR検索になります)</td>
</tr>
<tr>
<td>(5)</td>
<td>「(^o^)」のようなカッコで囲まれた文字列を検索したい場合は、「"(^o^)"」のように半角のダブルクオーテーション(")で囲って下さい。</td>
</tr>
</table>
<p class="set">msearchとはKatsushi Matsuda氏、毛流麦花氏が開発された、設置が容易で高速な全文検索エンジンです。<br>
オリジナル（アーカイブ）：<a href="https://web.archive.org/web/20181209073715/http://www.kiteya.net:80/script/msearch/">HP内全文検索エンジンmsearch</a><br>
Unicode対応版：<a href="http://www.marbacka.net/msearch/">Unicode版msearch</a><br>
SQLite3版：<a href="https://github.com/anineco/msearch">GitHub</a></p>
</article>
</main>
</div><!-- #container -->
</body>
</html>
EOS
}

#
# データベースを開く
#
my $dbh = DBI->connect('dbi:SQLite:dbname=default.db', '', '',
  { RaiseError => 1, PrintError => 0, sqlite_unicode => 1, ReadOnly => 1 }) or die $DBI::errstr;

#
# 検索式を得る
#
my $cgi = CGI->new;
my $query = $cgi->param('query');
utf8::decode($query) unless utf8::is_utf8($query);
$query =~ s/^\s*//;
$query =~ s/\s*$//;

unless (length $query) {
###############################
# HP内検索ヘルプを出力
###############################
  print_head('HP内検索ヘルプ', $query);

  my $row = $dbh->selectrow_hashref('SELECT COUNT(*) AS c,MAX(mtime) AS m FROM records');
  my $c = $row->{c};
  my $m = strftime('%F %T', localtime($row->{m}));

  print_status('ページ数：' . $c, '最終更新日時：' . $m);
  print_help();
} else {
###############################
# 検索実行と結果表示
###############################
  print_head('検索結果', $query);

#
# 検索式 → WHERE句条件式
#
  my $condition = ''; # WHERE句条件式
  my @c_words = (); # content のキーワード
  my @t_words = (); # title のキーワード

  my $q = $query;
  while (length $q) {
    if ($condition) {
      $condition .= ' AND';
    }
    if ($q =~ s/^\((.+?)\)//) { # (AAA BBB)
      my $s = $1;
      $s =~ s/^\s*//;
      my @terms = (); # キーワード
      while (length $s) {
        if ($s =~ s/^"(.+?)"// || $s =~ s/^(\S+)//) { # "AAA" または AAA
          push(@t_words, $1);
          push(@c_words, $1);
          push(@terms, $1);
        }
        $s =~ s/^\s*//;
      }
      $condition .= ' (' . join(' OR ', map {
        my $w = $_ =~ s/'/''/gr;
        "INSTR(title,'$w') OR INSTR(content,'$w')";
      } @terms) . ')';
    } elsif ($q =~ s/^-"(.+?)"// || $q =~ s/^-(\S+)//) { # -"AAA" または -AAA
      my $w = $1 =~ s/'/''/gr;
      $condition .= " NOT INSTR(content,'$w')";
    } elsif ($q =~ s/^[tT]:"(.+?)"// || $q =~ s/^[tT]:(\S+)//) { # t:"AAA" または t:AAA
      push(@t_words, $1);
      my $w = $1 =~ s/'/''/gr;
      $condition .= " INSTR(title,'$w')";
    } elsif ($q =~ s/^[uU]:"(.+?)"// || $q =~ s/^[uU]:(\S+)//) { # u:"AAA" または u:AAA
      my $w = $1 =~ s/'/''/gr;
      $condition .= " INSTR(url,'$w')";
    } elsif ($q =~ s/^"(.+?)"// || $q =~ s/^(\S+)//) { # "AAA" または AAA
      push(@t_words, $1);
      push(@c_words, $1);
      my $w = $1 =~ s/'/''/gr;
      $condition .= " (INSTR(title,'$w') OR INSTR(content,'$w'))";
    }
    $q =~ s/^\s*//;
  }

#
# 検索を実行
#
  my $s0 = times;
  my $c = $dbh->selectrow_hashref('SELECT COUNT(*) AS c FROM records WHERE' . $condition)->{c};

  my $sth = $dbh->prepare('SELECT * FROM records WHERE' . $condition . ' ORDER BY period DESC'); # 🔖 period でソート
  $sth->execute();
  my $m = sprintf '%.2f', times - $s0;

  print_status('ヒット数：' . $c, '検索に要した時間：' . $m . '秒');

#
# 検索結果を表示
#
  print '<dl>', "\n";
  my $seqno = 0;
  while (my $row = $sth->fetchrow_hashref) {
    ++$seqno;
    my $url = $row->{url};
    my $content = $row->{content};
    my $title = $row->{title};

    my $n = length($content);
    my $i = -1;
    my $kw = '';
    foreach my $w (@c_words) {
      my $k = index($content, $w);
      if ($k >= 0 && ($i < 0 || $k < $i)) {
        $i = $k;
        $kw = $w;
      }
    }
    $i -= 20; # 🔖 キーワードの前方20字
    if ($i < 0) {
      $i = 0;
    }
    my $j = $i + length($kw) + 60; # 🔖 キーワードの後方40字
    my $summary;
    if ($j < $n) {
      $summary = substr($content, $i, $j - $i) . '・・・';
    } else {
      $summary = substr($content, $i);
    }
    foreach my $w (@c_words) {
      my $k = index($summary, $w);
      if ($k >= 0) {
        substr $summary, $k, length($w), "\elt;b\egt;$w\elt;/b\egt;";
      }
    }
    $summary = htmlspecialchars($summary);
    $summary =~ s/\elt;/</g;
    $summary =~ s/\egt;/>/g;

    foreach my $w (@t_words) {
      my $k = index($title, $w);
      if ($k >= 0) {
        substr $title, $k, length($w), "\elt;b\egt;$w\elt;/b\egt;";
      }
    }
    $title = htmlspecialchars($title);
    $title =~ s/\elt;/</g;
    $title =~ s/\egt;/>/g;

    print <<"EOS";
<dt>$seqno. <a href="$url">$title</a></dt>
<dd><span class="url">$url</span><br>$summary</dd>
EOS
  }
  if ($seqno == 0) {
    print '<dt></dt><dd>検索結果なし</dd>', "\n";
  }
  print '</dl>', "\n";
  $sth->finish;

  print <<'EOS';
</article>
</main>
</div><!-- #container -->
</body>
</html>
EOS
}
$dbh->disconnect;
__END__
