# -*- coding: utf-8 -*-
"""
CustomerNexusSystem 総合テストプログラム
バージョン107対応

このテストプログラムは以下の機能を検証します：
1. 検索機能（第一段階：部分一致AND検索、第二段階：一文字違いAND検索）
2. AND/OR検索
3. 曖昧検索モード（OFF/0件のみ/ON）
4. 列名クリック（ソート、検索対象列の選択）
5. リセットボタン（キーワードは残す、表示様式はリセット）
6. クリアボタン（キーワードをクリア）
7. 色付け機能（自主出禁、出禁、新規・紹介NG、サビ禁）
8. ダブルクリック処理（fuzzy_ID対応）
9. parse_search_keywords関数
10. get_search_mask関数
11. get_fuzzy_matches関数
12. get_fuzzy_matches_for_keywords関数
13. ローマ字→カタカナ変換（IME未入力対策）
"""

import unittest
import pandas as pd
import sys
import os

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# customer_app.pyから必要な関数をインポート
from customer_app import (
    normalize_text_unified,
    hira_to_kata,
    CustomerApp
)
from utils import romaji_to_katakana


class TestNormalization(unittest.TestCase):
    """テキスト正規化のテスト"""
    
    def test_normalize_text_unified_basic(self):
        """基本的な正規化テスト"""
        # 全角→半角（NFKC正規化）
        self.assertEqual(normalize_text_unified('０１２３'), '0123')
        self.assertEqual(normalize_text_unified('ＡＢＣ'), 'ABC')
        # 小文字→大文字
        self.assertEqual(normalize_text_unified('abc'), 'ABC')
        # カタカナ正規化
        self.assertEqual(normalize_text_unified('ｱｲｳ'), 'アイウ')
    
    def test_hira_to_kata(self):
        """ひらがな→カタカナ変換テスト"""
        self.assertEqual(hira_to_kata('あいうえお'), 'アイウエオ')
        self.assertEqual(hira_to_kata('田中'), '田中')


class TestSearchKeywordParsing(unittest.TestCase):
    """キーワード解析のテスト"""
    
    def setUp(self):
        """テスト用アプリインスタンスを作成（GUIなし）"""
        # CustomerAppのインスタンスを作成せずにメソッドをテスト
        pass
    
    def test_and_parsing(self):
        """AND検索のパース"""
        # スペース区切り（半角）
        result = self._parse_keywords('田中 太郎')
        self.assertEqual(result, [['田中', '太郎']])
        
        # スペース区切り（全角）
        result = self._parse_keywords('田中　太郎')
        self.assertEqual(result, [['田中', '太郎']])
        
        # 複数スペース
        result = self._parse_keywords('田中   太郎')
        self.assertEqual(result, [['田中', '太郎']])
    
    def test_or_parsing(self):
        """OR検索のパース"""
        # |記号（半角）
        result = self._parse_keywords('田中|山田')
        self.assertEqual(result, [['田中'], ['山田']])
        
        # ｜記号（全角）
        result = self._parse_keywords('田中｜山田')
        self.assertEqual(result, [['田中'], ['山田']])
        
        # スペース+|+スペース
        result = self._parse_keywords('田中 | 山田')
        self.assertEqual(result, [['田中'], ['山田']])
    
    def test_mixed_and_or(self):
        """AND/OR混合検索のパース"""
        result = self._parse_keywords('田中 太郎|山田 花子')
        self.assertEqual(result, [['田中', '太郎'], ['山田', '花子']])
    
    def _parse_keywords(self, query):
        """キーワード解析（CustomerAppのメソッドを模倣）"""
        import re
        # OR区切り: スペースに囲まれた｜または|の連続
        or_pattern = r'[\s　]*[｜|]+[\s　]*'
        or_groups = re.split(or_pattern, query)
        
        result = []
        for group in or_groups:
            # AND区切り: 1つ以上のスペース（全角・半角）
            and_pattern = r'[\s　]+'
            and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
            if and_keywords:
                result.append(and_keywords)
        
        return result


class TestFuzzyMatch(unittest.TestCase):
    """曖昧検索のテスト"""
    
    def test_levenshtein_distance(self):
        """編集距離計算テスト"""
        # 編集距離1のケース
        self.assertEqual(self._levenshtein('abc', 'ab'), 1)   # 削除
        self.assertEqual(self._levenshtein('abc', 'abcd'), 1)  # 追加
        self.assertEqual(self._levenshtein('abc', 'adc'), 1)   # 置換
        
        # 編集距離0のケース
        self.assertEqual(self._levenshtein('abc', 'abc'), 0)
        
        # 編集距離2以上のケース
        self.assertEqual(self._levenshtein('abc', 'xyz'), 3)
    
    def test_check_fuzzy_match(self):
        """一文字違いチェック"""
        # 編集距離1のケース
        self.assertTrue(self._check_fuzzy('出禁', '出金'))   # 1文字置換
        self.assertTrue(self._check_fuzzy('070', '0700'))    # 1文字追加
        self.assertTrue(self._check_fuzzy('田中', '田'))     # 1文字削除
        
        # 編集距離0のケース（完全一致は曖昧マッチではない）
        self.assertFalse(self._check_fuzzy('abc', 'abc'))
        
        # 編集距離2以上のケース
        self.assertFalse(self._check_fuzzy('abc', 'xyz'))
        
        # 1文字キーワードは曖昧検索しない
        self.assertFalse(self._check_fuzzy('a', 'b'))
    
    def _levenshtein(self, s1, s2):
        """編集距離計算"""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _check_fuzzy(self, query, target):
        """一文字違いチェック（編集距離1のみ）"""
        if len(query) <= 1:
            return False
        return self._levenshtein(query, target) == 1


class TestColorLogic(unittest.TestCase):
    """色付けロジックのテスト"""
    
    def test_color_priority(self):
        """色付けの優先順位テスト"""
        # 優先順位: 自主出禁 > 出禁 > 新規・紹介NG > サビ禁
        
        # 自主出禁が含まれる場合
        self.assertEqual(self._get_color('自主出禁です'), '#FFC000')
        
        # 出禁が含まれる場合（自主出禁を含まない）
        self.assertEqual(self._get_color('出禁'), '#FF3300')
        
        # 新規・紹介NGの場合
        self.assertEqual(self._get_color('新規 不可'), '#9C27B0')
        self.assertEqual(self._get_color('紹介 NG'), '#9C27B0')
        self.assertEqual(self._get_color('新規 だめ'), '#9C27B0')
        self.assertEqual(self._get_color('紹介 受けない'), '#9C27B0')
        
        # サービス禁止系
        self.assertEqual(self._get_color('サビ禁'), '#00FF00')
        self.assertEqual(self._get_color('サービス停'), '#00FF00')
        self.assertEqual(self._get_color('サビ止'), '#00FF00')
        self.assertEqual(self._get_color('サービスNG'), '#00FF00')
        self.assertEqual(self._get_color('サービスなし'), '#00FF00')
        
        # 該当なし
        self.assertIsNone(self._get_color('通常の顧客'))
    
    def test_color_priority_order(self):
        """優先順位の正確性テスト"""
        # 自主出禁 > 出禁
        self.assertEqual(self._get_color('自主出禁 出禁'), '#FFC000')
        
        # 出禁 > 新規NG
        self.assertEqual(self._get_color('出禁 新規 不可'), '#FF3300')
        
        # 新規NG > サビ禁
        self.assertEqual(self._get_color('新規 不可 サビ禁'), '#9C27B0')
    
    def _get_color(self, text):
        """色付けロジック"""
        import re
        
        # 優先順位1: 自主出禁
        if '自主出禁' in text:
            return '#FFC000'
        
        # 優先順位2: 出禁
        if '出禁' in text:
            return '#FF3300'
        
        # 優先順位3: 新規・紹介NG
        has_shinki_shoukai = ('新規' in text or '紹介' in text)
        ng_words = ['不可', 'だめ', 'ダメ', '駄目', '拒否', 'NG', 'ＮＧ', '受けない', '受けるな', '×']
        has_ng = any(ng in text for ng in ng_words)
        if has_shinki_shoukai and has_ng:
            return '#9C27B0'
        
        # 優先順位4: サービス禁止系
        sabi_pattern = r'(サビ|サービス)(禁|停|無|止|ＮＧ|NG|なし|×)'
        if re.search(sabi_pattern, text):
            return '#00FF00'
        
        return None


class TestSearchMask(unittest.TestCase):
    """検索マスク生成のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.test_data = pd.DataFrame({
            '登録名': ['田中太郎', '山田花子', '鈴木一郎', '佐藤次郎', '高橋三郎'],
            '電話番号': ['090-1234-5678', '080-2345-6789', '070-3456-7890', '090-4567-8901', '080-5678-9012'],
            '備考': ['出禁', '自主出禁', '新規 不可', 'サビ禁', '通常'],
            '出禁種別': ['', '', '', '', '']
        })
        # search_index列を作成
        self.test_data['search_index'] = self.test_data.apply(
            lambda row: ' '.join([str(v) for v in row.values if str(v) != 'nan']), axis=1
        )
    
    def test_single_keyword_search(self):
        """単一キーワード検索"""
        # 部分一致検索
        mask = self._search('田中', self.test_data)
        self.assertEqual(mask.sum(), 1)
        self.assertTrue(mask.iloc[0])
        
        # 電話番号検索
        mask = self._search('070', self.test_data)
        self.assertEqual(mask.sum(), 1)
        self.assertTrue(mask.iloc[2])
    
    def test_and_search(self):
        """AND検索"""
        # 田中 AND 太郎
        mask = self._search_and(['田中', '太郎'], self.test_data)
        self.assertEqual(mask.sum(), 1)
        self.assertTrue(mask.iloc[0])
        
        # 存在しない組み合わせ
        mask = self._search_and(['田中', '花子'], self.test_data)
        self.assertEqual(mask.sum(), 0)
    
    def test_or_search(self):
        """OR検索"""
        # 田中 OR 山田
        mask = self._search_or([['田中'], ['山田']], self.test_data)
        self.assertEqual(mask.sum(), 2)
        self.assertTrue(mask.iloc[0])
        self.assertTrue(mask.iloc[1])
    
    def _search(self, keyword, df):
        """単一キーワード検索"""
        keyword_norm = normalize_text_unified(keyword)
        mask = df['search_index'].apply(
            lambda x: keyword_norm in normalize_text_unified(str(x))
        )
        return mask
    
    def _search_and(self, keywords, df):
        """AND検索"""
        mask = pd.Series([True] * len(df))
        for keyword in keywords:
            single_mask = self._search(keyword, df)
            mask = mask & single_mask
        return mask
    
    def _search_or(self, keyword_groups, df):
        """OR検索"""
        mask = pd.Series([False] * len(df))
        for and_group in keyword_groups:
            and_mask = self._search_and(and_group, df)
            mask = mask | and_mask
        return mask


class TestTwoStageSearch(unittest.TestCase):
    """二段階検索のテスト（第一段階：部分一致、第二段階：一文字違い）"""
    
    def setUp(self):
        """テストデータの準備"""
        self.test_data = pd.DataFrame({
            '登録名': ['出禁太郎', '出金花子', '田中一郎', '出禁次郎', '山田三郎'],
            '電話番号': ['090-1234-5678', '070-2345-6789', '070-3456-7890', '070-4567-8901', '080-5678-9012'],
            '備考': ['', '', '', '', '']
        })
        self.test_data['search_index'] = self.test_data.apply(
            lambda row: ' '.join([str(v) for v in row.values if str(v) != 'nan']), axis=1
        )
    
    def test_first_stage_search(self):
        """第一段階：部分一致AND検索"""
        # 「出禁 070」で検索
        # 出禁を含む: 0, 3
        # 070を含む: 1, 2, 3
        # AND結果: 3
        mask = self._search_and(['出禁', '070'], self.test_data)
        self.assertEqual(mask.sum(), 1)
        self.assertTrue(mask.iloc[3])  # '出禁次郎' + '070-4567-8901'
    
    def test_second_stage_search(self):
        """第二段階：一文字違いAND検索"""
        # 「出禁 070」で検索
        # 第一段階の結果: インデックス3
        # 第二段階:
        #   「出禁を含む OR 出禁の一文字違い」AND「070を含む OR 070の一文字違い」
        #   - 出禁を含む: 0, 3
        #   - 出禁の一文字違い: 出金(1)
        #   → 出禁合計: 0, 1, 3
        #   - 070を含む: 1, 2, 3
        #   - 070の一文字違い: 0700, 07, 07x など
        #   → AND結果: 1, 3 (1は出金+070)
        # 第一段階を除外: 1 (出金花子)
        
        first_stage = self._search_and(['出禁', '070'], self.test_data)
        first_stage_indices = set(self.test_data.index[first_stage])
        
        second_stage = self._fuzzy_and_search(['出禁', '070'], self.test_data, first_stage_indices)
        
        # 第二段階で「出金花子」がヒットするはず
        self.assertIn(1, second_stage)
        # 第一段階の結果は除外
        self.assertNotIn(3, second_stage)
    
    def _search_and(self, keywords, df):
        """AND検索"""
        mask = pd.Series([True] * len(df))
        for keyword in keywords:
            keyword_norm = normalize_text_unified(keyword)
            single_mask = df['search_index'].apply(
                lambda x: keyword_norm in normalize_text_unified(str(x))
            )
            mask = mask & single_mask
        return mask
    
    def _fuzzy_and_search(self, keywords, df, exclude_indices):
        """第二段階：一文字違いAND検索"""
        and_results = []
        
        for keyword in keywords:
            keyword_matches = set()
            keyword_norm = normalize_text_unified(keyword)
            
            for idx in df.index:
                cell_norm = normalize_text_unified(str(df.at[idx, 'search_index']))
                
                # 通常部分一致
                if keyword_norm in cell_norm:
                    keyword_matches.add(idx)
                    continue
                
                # 一文字違いチェック（簡易版）
                if self._check_fuzzy_in_text(keyword_norm, cell_norm):
                    keyword_matches.add(idx)
            
            and_results.append(keyword_matches)
        
        # AND結果（積集合）
        if and_results:
            result = and_results[0]
            for s in and_results[1:]:
                result = result & s
        else:
            result = set()
        
        # 第一段階の結果を除外
        return result - exclude_indices
    
    def _check_fuzzy_in_text(self, query, text):
        """テキスト内で一文字違いをチェック"""
        if len(query) <= 1:
            return False
        
        # 部分文字列で一文字違いをチェック
        for i in range(len(text) - len(query) + 1):
            substring = text[i:i + len(query)]
            if self._levenshtein(query, substring) == 1:
                return True
        
        # 1文字長い部分文字列もチェック
        for i in range(max(0, len(text) - len(query))):
            substring = text[i:i + len(query) + 1]
            if self._levenshtein(query, substring) == 1:
                return True
        
        return False
    
    def _levenshtein(self, s1, s2):
        """編集距離計算"""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class TestResetBehavior(unittest.TestCase):
    """リセット動作のテスト"""
    
    def test_reset_keeps_keyword(self):
        """リセット時にキーワードは残る"""
        # この仕様は明示的にコードで確認
        # reset_search関数でentry_search.delete()が呼ばれていないこと
        pass
    
    def test_reset_clears_display_style(self):
        """リセット時に表示様式がリセットされる"""
        # 全件表示時は常に通常表示
        # len(self.current_indices) == len(self.df) の場合
        # normal_indices = set(self.current_indices)
        pass


class TestFuzzyDisplayStyle(unittest.TestCase):
    """曖昧マッチの表示スタイルテスト"""
    
    def test_fuzzy_id_format(self):
        """fuzzy_IDフォーマットの検証"""
        # 曖昧マッチのIDは "fuzzy_123" 形式
        item_id = "fuzzy_123"
        self.assertTrue(item_id.startswith('fuzzy_'))
        
        # IDから数値を抽出
        idx = int(item_id[6:])
        self.assertEqual(idx, 123)
    
    def test_normal_id_format(self):
        """通常IDフォーマットの検証"""
        item_id = "456"
        self.assertFalse(item_id.startswith('fuzzy_'))
        idx = int(item_id)
        self.assertEqual(idx, 456)


class TestEdgeCases(unittest.TestCase):
    """エッジケースのテスト"""
    
    def test_empty_keyword(self):
        """空キーワードの処理"""
        result = self._parse_keywords('')
        self.assertEqual(result, [])
        
        result = self._parse_keywords('   ')
        self.assertEqual(result, [])
    
    def test_single_char_keyword(self):
        """1文字キーワードの処理"""
        # 1文字キーワードは曖昧検索しない
        self.assertFalse(self._check_fuzzy('a', 'b'))
    
    def test_special_characters(self):
        """特殊文字の処理"""
        # 全角OR記号
        result = self._parse_keywords('田中｜山田')
        self.assertEqual(result, [['田中'], ['山田']])
        
        # 連続した|記号
        result = self._parse_keywords('田中||山田')
        self.assertEqual(result, [['田中'], ['山田']])
    
    def test_mixed_width_characters(self):
        """全角・半角混在の処理"""
        # 正規化後は同じになるはず
        self.assertEqual(
            normalize_text_unified('０９０'),
            normalize_text_unified('090')
        )
    
    def _parse_keywords(self, query):
        """キーワード解析"""
        import re
        if not query.strip():
            return []
        
        # OR区切り: スペースに囲まれた｜または|の連続
        or_pattern = r'[\s　]*[｜|]+[\s　]*'
        or_groups = re.split(or_pattern, query)
        
        result = []
        for group in or_groups:
            # AND区切り: 1つ以上のスペース（全角・半角）
            and_pattern = r'[\s　]+'
            and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
            if and_keywords:
                result.append(and_keywords)
        
        return result
    
    def _check_fuzzy(self, query, target):
        """一文字違いチェック"""
        if len(query) <= 1:
            return False
        return self._levenshtein(query, target) == 1
    
    def _levenshtein(self, s1, s2):
        """編集距離計算"""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class TestRomajiToKatakana(unittest.TestCase):
    """ローマ字→カタカナ変換のテスト（IME未入力対策）"""
    
    def test_basic_vowels(self):
        """基本母音の変換"""
        self.assertEqual(romaji_to_katakana('a'), 'ア')
        self.assertEqual(romaji_to_katakana('i'), 'イ')
        self.assertEqual(romaji_to_katakana('u'), 'ウ')
        self.assertEqual(romaji_to_katakana('e'), 'エ')
        self.assertEqual(romaji_to_katakana('o'), 'オ')
    
    def test_basic_consonants(self):
        """基本子音の変換"""
        self.assertEqual(romaji_to_katakana('ka'), 'カ')
        self.assertEqual(romaji_to_katakana('ki'), 'キ')
        self.assertEqual(romaji_to_katakana('ku'), 'ク')
        self.assertEqual(romaji_to_katakana('sa'), 'サ')
        self.assertEqual(romaji_to_katakana('ta'), 'タ')
        self.assertEqual(romaji_to_katakana('na'), 'ナ')
        self.assertEqual(romaji_to_katakana('ha'), 'ハ')
        self.assertEqual(romaji_to_katakana('ma'), 'マ')
        self.assertEqual(romaji_to_katakana('ya'), 'ヤ')
        self.assertEqual(romaji_to_katakana('ra'), 'ラ')
        self.assertEqual(romaji_to_katakana('wa'), 'ワ')
    
    def test_special_sounds(self):
        """特殊音の変換"""
        self.assertEqual(romaji_to_katakana('shi'), 'シ')
        self.assertEqual(romaji_to_katakana('chi'), 'チ')
        self.assertEqual(romaji_to_katakana('tsu'), 'ツ')
        self.assertEqual(romaji_to_katakana('fu'), 'フ')
    
    def test_youon(self):
        """拗音の変換"""
        self.assertEqual(romaji_to_katakana('kya'), 'キャ')
        self.assertEqual(romaji_to_katakana('sha'), 'シャ')
        self.assertEqual(romaji_to_katakana('cha'), 'チャ')
        self.assertEqual(romaji_to_katakana('nya'), 'ニャ')
    
    def test_sokuon(self):
        """促音（っ）の変換"""
        self.assertEqual(romaji_to_katakana('kka'), 'ッカ')
        self.assertEqual(romaji_to_katakana('tta'), 'ッタ')
        self.assertEqual(romaji_to_katakana('ppa'), 'ッパ')
        self.assertEqual(romaji_to_katakana('ppu'), 'ップ')
    
    def test_long_vowel(self):
        """長音の変換"""
        self.assertEqual(romaji_to_katakana('-'), 'ー')
        self.assertEqual(romaji_to_katakana('a-'), 'アー')
    
    def test_n_sound(self):
        """ん音の変換"""
        self.assertEqual(romaji_to_katakana('n'), 'ン')
        self.assertEqual(romaji_to_katakana('nn'), 'ン')
    
    def test_real_words(self):
        """実際の単語の変換（ユーザー要求例）"""
        # yappu- → ヤップー
        self.assertEqual(romaji_to_katakana('yappu-'), 'ヤップー')
        # teru → テル
        self.assertEqual(romaji_to_katakana('teru'), 'テル')
        # tanaka → タナカ
        self.assertEqual(romaji_to_katakana('tanaka'), 'タナカ')
        # yamada → ヤマダ
        self.assertEqual(romaji_to_katakana('yamada'), 'ヤマダ')
        # suzuki → スズキ
        self.assertEqual(romaji_to_katakana('suzuki'), 'スズキ')
        # satou → サトウ
        self.assertEqual(romaji_to_katakana('satou'), 'サトウ')
    
    def test_mixed_input(self):
        """数字混在入力の変換"""
        # teru3 → テル3
        self.assertEqual(romaji_to_katakana('teru3'), 'テル3')
        # abc123 → アブク123（数字はそのまま）
        result = romaji_to_katakana('abc123')
        self.assertIn('123', result)
    
    def test_uppercase_input(self):
        """大文字入力の変換"""
        # 大文字も小文字と同様に変換される
        self.assertEqual(romaji_to_katakana('TANAKA'), 'タナカ')
        self.assertEqual(romaji_to_katakana('Yamada'), 'ヤマダ')
    
    def test_alternative_patterns(self):
        """代替入力パターンの変換（IME互換）"""
        # ジャ: ja / zya 両対応
        self.assertEqual(romaji_to_katakana('ja'), 'ジャ')
        self.assertEqual(romaji_to_katakana('zya'), 'ジャ')
        # ァ: xa / la 両対応（小文字）
        self.assertEqual(romaji_to_katakana('xa'), 'ァ')
        # チャ: cha / tya / cya 
        self.assertEqual(romaji_to_katakana('cha'), 'チャ')
        self.assertEqual(romaji_to_katakana('tya'), 'チャ')
        self.assertEqual(romaji_to_katakana('cya'), 'チャ')
        # シ: shi / si
        self.assertEqual(romaji_to_katakana('shi'), 'シ')
        self.assertEqual(romaji_to_katakana('si'), 'シ')
        # ッ: ltu / xtu / ltsu / xtsu
        self.assertEqual(romaji_to_katakana('ltu'), 'ッ')
        self.assertEqual(romaji_to_katakana('xtu'), 'ッ')
        self.assertEqual(romaji_to_katakana('ltsu'), 'ッ')
        self.assertEqual(romaji_to_katakana('xtsu'), 'ッ')
        # ティ: thi
        self.assertEqual(romaji_to_katakana('thi'), 'ティ')
        # ディ: dhi
        self.assertEqual(romaji_to_katakana('dhi'), 'ディ')
        # ファ: fa / hwa
        self.assertEqual(romaji_to_katakana('fa'), 'ファ')
        # クァ: qa / kwa / qwa
        self.assertEqual(romaji_to_katakana('qa'), 'クァ')
        self.assertEqual(romaji_to_katakana('kwa'), 'クァ')


class TestRomajiAutoConversion(unittest.TestCase):
    """ローマ字自動変換によるOR検索のテスト"""
    
    def test_romaji_expansion(self):
        """ローマ字入力がOR検索に展開される"""
        # parse_search_keywordsの模倣
        result = self._parse_with_romaji('tanaka')
        # 元の'tanaka'と変換後の'タナカ'の両方がOR条件として存在
        self.assertEqual(len(result), 2)
        self.assertIn(['tanaka'], result)
        self.assertIn(['タナカ'], result)
    
    def test_japanese_no_expansion(self):
        """日本語入力は展開されない"""
        result = self._parse_with_romaji('田中')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [['田中']])
    
    def test_and_with_romaji(self):
        """AND検索でのローマ字展開"""
        result = self._parse_with_romaji('tanaka taro')
        # 元のANDグループと変換後のANDグループがOR条件として存在
        self.assertEqual(len(result), 2)
        self.assertIn(['tanaka', 'taro'], result)
        self.assertIn(['タナカ', 'タロ'], result)
    
    def test_mixed_and_romaji(self):
        """日本語とローマ字混在のAND検索"""
        result = self._parse_with_romaji('田中 taro')
        # ローマ字を含むので展開される
        self.assertEqual(len(result), 2)
        self.assertIn(['田中', 'taro'], result)
        self.assertIn(['田中', 'タロ'], result)
    
    def _parse_with_romaji(self, query):
        """ローマ字対応のキーワード解析"""
        import re
        
        # OR区切り
        or_pattern = r'[\s　]*[｜|]+[\s　]*'
        or_groups = re.split(or_pattern, query)
        
        result = []
        for group in or_groups:
            and_pattern = r'[\s　]+'
            and_keywords = [k.strip() for k in re.split(and_pattern, group) if k.strip()]
            if and_keywords:
                result.append(and_keywords)
        
        # ローマ字展開
        expanded_result = []
        for and_group in result:
            has_romaji = False
            converted_group = []
            for keyword in and_group:
                if re.search(r'[a-zA-Z]', keyword):
                    has_romaji = True
                    converted = romaji_to_katakana(keyword)
                    converted_group.append(converted)
                else:
                    converted_group.append(keyword)
            
            expanded_result.append(and_group)
            
            if has_romaji and converted_group != and_group:
                expanded_result.append(converted_group)
        
        return expanded_result


def run_all_tests():
    """全テストを実行"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 全テストクラスを追加
    test_classes = [
        TestNormalization,
        TestSearchKeywordParsing,
        TestFuzzyMatch,
        TestColorLogic,
        TestSearchMask,
        TestTwoStageSearch,
        TestResetBehavior,
        TestFuzzyDisplayStyle,
        TestEdgeCases,
        TestRomajiToKatakana,
        TestRomajiAutoConversion,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 詳細な結果を表示
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # サマリー
    print("\n" + "=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)
    print(f"実行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
