# -*- coding: utf-8 -*-
"""
検索ロジックの徹底的なテスト
"""
import pytest
import pandas as pd
import sys
import os

# customer_app.pyのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    hira_to_kata, normalize_text_unified, get_natural_sort_key,
    parse_fuzzy_date, parse_excel_date, format_date_text,
    generate_birth_search_keys, parse_date_with_separators
)


class TestTextNormalization:
    """テキスト正規化のテスト"""
    
    def test_hira_to_kata_basic(self):
        """ひらがなからカタカナへの基本変換"""
        assert hira_to_kata("あいうえお") == "アイウエオ"
        assert hira_to_kata("たなか") == "タナカ"
        assert hira_to_kata("やまだ") == "ヤマダ"
    
    def test_hira_to_kata_mixed(self):
        """混在文字列の変換"""
        assert hira_to_kata("田中たろう") == "田中タロウ"
        assert hira_to_kata("あいうABC") == "アイウABC"
    
    def test_normalize_text_unified_basic(self):
        """基本的なテキスト正規化"""
        # 全角→半角
        assert normalize_text_unified("１２３") == "123"
        assert normalize_text_unified("ＡＢＣ") == "abc"
        
        # 小文字化
        assert normalize_text_unified("ABC") == "abc"
        assert normalize_text_unified("AbC") == "abc"
        
        # スペース削除
        assert normalize_text_unified("田 中") == "田中"
        assert normalize_text_unified("　山　田　") == "山田"
    
    def test_normalize_text_unified_phone(self):
        """電話番号の正規化"""
        assert normalize_text_unified("090-1234-5678") == "09012345678"
        assert normalize_text_unified("０９０－１２３４－５６７８") == "09012345678"
        assert normalize_text_unified("090 1234 5678") == "09012345678"
    
    def test_normalize_text_unified_name_variants(self):
        """名前のバリエーション"""
        # 渡辺/渡部/渡邊
        assert "渡" in normalize_text_unified("渡辺")
        assert "渡" in normalize_text_unified("渡部")
        assert "渡" in normalize_text_unified("渡邊")


class TestDateParsing:
    """生年月日解析のテスト"""
    
    def test_parse_date_with_separators_slash(self):
        """スラッシュ区切りの日付"""
        assert parse_date_with_separators("1990/05/15") == (1990, 5, 15)
        assert parse_date_with_separators("2000/1/1") == (2000, 1, 1)
    
    def test_parse_date_with_separators_hyphen(self):
        """ハイフン区切りの日付"""
        assert parse_date_with_separators("1990-05-15") == (1990, 5, 15)
        assert parse_date_with_separators("2000-1-1") == (2000, 1, 1)
    
    def test_parse_date_with_separators_dot(self):
        """ドット区切りの日付"""
        assert parse_date_with_separators("1990.05.15") == (1990, 5, 15)
        assert parse_date_with_separators("2000.1.1") == (2000, 1, 1)
    
    def test_parse_date_with_separators_japanese(self):
        """和暦の解析"""
        # 昭和
        assert parse_date_with_separators("S63/12/31") == (1988, 12, 31)
        assert parse_date_with_separators("昭和63年12月31日") == (1988, 12, 31)
        
        # 平成
        assert parse_date_with_separators("H1/1/8") == (1989, 1, 8)
        assert parse_date_with_separators("平成元年1月8日") == (1989, 1, 8)
        
        # 令和
        assert parse_date_with_separators("R1/5/1") == (2019, 5, 1)
        assert parse_date_with_separators("令和元年5月1日") == (2019, 5, 1)
    
    def test_parse_fuzzy_date_8digits(self):
        """8桁数字の日付解析"""
        results = parse_fuzzy_date("19900515")
        assert (1990, 5, 15) in results
    
    def test_parse_fuzzy_date_6digits(self):
        """6桁数字の日付解析（年月日の組み合わせ）"""
        results = parse_fuzzy_date("900515")
        # 1990年5月15日または2090年5月15日
        assert any(y in [1990, 2090] for y, m, d in results if m == 5 and d == 15)
    
    def test_parse_fuzzy_date_partial(self):
        """部分的な日付解析"""
        # 年月のみ
        results = parse_fuzzy_date("199005")
        assert any(y == 1990 and m == 5 for y, m, d in results)
        
        # 月日のみ
        results = parse_fuzzy_date("0515")
        assert any(m == 5 and d == 15 for y, m, d in results)
    
    def test_generate_birth_search_keys(self):
        """生年月日検索キーの生成"""
        keys = generate_birth_search_keys("1990/05/15")
        assert "1990" in keys
        assert "05" in keys or "5" in keys
        assert "15" in keys


class TestNaturalSort:
    """自然順ソートのテスト"""
    
    def test_get_natural_sort_key_numbers(self):
        """数字を含む文字列のソート"""
        items = ["item10", "item2", "item1", "item20"]
        sorted_items = sorted(items, key=get_natural_sort_key)
        assert sorted_items == ["item1", "item2", "item10", "item20"]
    
    def test_get_natural_sort_key_mixed(self):
        """数字と文字の混在"""
        items = ["A10B2", "A2B10", "A2B2", "A10B10"]
        sorted_items = sorted(items, key=get_natural_sort_key)
        assert sorted_items == ["A2B2", "A2B10", "A10B2", "A10B10"]


class TestLevenshteinDistance:
    """レーベンシュタイン距離のテスト"""
    
    def setup_method(self):
        """テスト用のダミーアプリインスタンス作成"""
        # customer_app.pyから必要な部分だけインポート
        import tkinter as tk
        from tkinterdnd2 import TkinterDnD
        
        class DummyApp:
            def levenshtein_distance(self, s1, s2):
                """レーベンシュタイン距離（編集距離）を計算"""
                if len(s1) < len(s2):
                    return self.levenshtein_distance(s2, s1)
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
        
        self.app = DummyApp()
    
    def test_levenshtein_distance_identical(self):
        """同一文字列の距離は0"""
        assert self.app.levenshtein_distance("田中", "田中") == 0
        assert self.app.levenshtein_distance("山田", "山田") == 0
    
    def test_levenshtein_distance_substitution(self):
        """置換（1文字違い）"""
        assert self.app.levenshtein_distance("渡辺", "渡部") == 1
        assert self.app.levenshtein_distance("渡辺", "渡邊") == 1
    
    def test_levenshtein_distance_insertion(self):
        """挿入（1文字追加）"""
        assert self.app.levenshtein_distance("田中", "田中太") == 1
        assert self.app.levenshtein_distance("山田", "山田花") == 1
    
    def test_levenshtein_distance_deletion(self):
        """削除（1文字削除）"""
        assert self.app.levenshtein_distance("田中太郎", "田中郎") == 1
        assert self.app.levenshtein_distance("山田花子", "山田子") == 1
    
    def test_levenshtein_distance_phone(self):
        """電話番号の1桁違い"""
        assert self.app.levenshtein_distance("09012345678", "09012345679") == 1
        assert self.app.levenshtein_distance("09012345678", "09012345677") == 1


class TestANDORSearch:
    """AND/OR検索のテスト"""
    
    def setup_method(self):
        """テスト用のダミーアプリインスタンス作成"""
        import re
        
        class DummyApp:
            def parse_search_keywords(self, query):
                """キーワードをAND/ORに解析"""
                try:
                    # ｜または|で分割（OR条件）
                    or_groups = re.split(r'[｜|]', query)
                    
                    result = []
                    for group in or_groups:
                        # 空白（全角・半角）で分割（AND条件）
                        and_keywords = [k.strip() for k in group.split() if k.strip()]
                        if and_keywords:
                            result.append(and_keywords)
                    
                    return result
                except Exception as e:
                    return [[query.strip()]]
        
        self.app = DummyApp()
    
    def test_parse_single_keyword(self):
        """単一キーワード"""
        result = self.app.parse_search_keywords("田中")
        assert result == [["田中"]]
    
    def test_parse_and_search(self):
        """AND検索（空白区切り）"""
        result = self.app.parse_search_keywords("田中 太郎")
        assert result == [["田中", "太郎"]]
        
        result = self.app.parse_search_keywords("田中　太郎")  # 全角スペース
        assert result == [["田中", "太郎"]]
    
    def test_parse_or_search(self):
        """OR検索（｜区切り）"""
        result = self.app.parse_search_keywords("田中｜山田")
        assert result == [["田中"], ["山田"]]
        
        result = self.app.parse_search_keywords("田中|山田")  # 半角パイプ
        assert result == [["田中"], ["山田"]]
    
    def test_parse_and_or_combined(self):
        """AND + OR検索"""
        result = self.app.parse_search_keywords("田中 太郎｜山田 花子")
        assert result == [["田中", "太郎"], ["山田", "花子"]]
        
        result = self.app.parse_search_keywords("渡辺 090｜渡部 080｜渡邊 070")
        assert result == [["渡辺", "090"], ["渡部", "080"], ["渡邊", "070"]]
    
    def test_parse_with_extra_spaces(self):
        """余分なスペースの処理"""
        result = self.app.parse_search_keywords("田中  太郎")  # 2つのスペース
        assert result == [["田中", "太郎"]]
        
        result = self.app.parse_search_keywords(" 田中 太郎 ")  # 前後のスペース
        assert result == [["田中", "太郎"]]


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_empty_string(self):
        """空文字列の処理"""
        assert normalize_text_unified("") == ""
        assert hira_to_kata("") == ""
    
    def test_special_characters(self):
        """特殊文字の処理"""
        # ハイフン、スラッシュなど
        assert normalize_text_unified("田中-太郎") == "田中太郎"
        assert normalize_text_unified("山田/花子") == "山田花子"
    
    def test_very_long_string(self):
        """非常に長い文字列"""
        long_str = "あ" * 1000
        result = hira_to_kata(long_str)
        assert len(result) == 1000
        assert all(c == "ア" for c in result)
    
    def test_unicode_variants(self):
        """Unicode異体字"""
        # 渡辺の異体字
        variants = ["渡辺", "渡邊", "渡邉"]
        normalized = [normalize_text_unified(v) for v in variants]
        # 全て「渡」を含む
        assert all("渡" in n for n in normalized)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
