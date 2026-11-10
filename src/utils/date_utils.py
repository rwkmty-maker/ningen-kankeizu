# -*- coding: utf-8 -*-
import re
import datetime
import unicodedata
import pandas as pd


# 元号オフセット定数（昭和・平成・令和のみ）
ERA_OFFSETS = {'S': 1926, 'H': 1989, 'R': 2019}

# 元号の漢字表記マッピング
ERA_KANJI_MAP = {
    '昭和': 'S', '昭': 'S', 'しょうわ': 'S', 'ショウワ': 'S',
    '平成': 'H', '平': 'H', 'へいせい': 'H', 'ヘイセイ': 'H',
    '令和': 'R', '令': 'R', 'れいわ': 'R', 'レイワ': 'R'
}


def parse_fuzzy_date(query):
    """
    曖昧な数字列から日付候補リストを生成（完全版）
    元号はS/H/Rのみ、100歳以上は除外
    漢字表記の元号にも対応（昭和60、昭60、昭.60など）
    1桁から10桁まで全てのパターンを網羅
    
    戻り値: [(year, month, day), ...] のリスト（Noneは未指定を意味）
    """
    if not query or not str(query).strip():
        return []
    
    try:
        candidates = []
        query_norm = unicodedata.normalize('NFKC', str(query))
        current_year = datetime.datetime.now().year
        min_year = current_year - 100  # 100歳以上は除外
    except Exception as e:
        return []
    
    # 1. 和暦パターン（元号あり）漢字表記も対応
    try:
        # 漢字表記の元号を英字に変換
        era_char = None
        query_for_parse = query_norm
        
        for kanji, eng in ERA_KANJI_MAP.items():
            if query_norm.startswith(kanji):
                era_char = eng
                query_for_parse = eng + query_norm[len(kanji):]
                break
        
        # 英字を大文字に統一
        query_upper = query_for_parse.upper()
        
        # S1, H2, R3 のような年のみのパターン（ドット区切りも対応: S.51）
        match_era_year = re.match(r'^([SHR])\.?(\d{1,2})$', query_upper)
        if match_era_year:
            era, y = match_era_year.groups()
            if era in ERA_OFFSETS:
                y_west = ERA_OFFSETS[era] + int(y) - 1
                if y_west >= min_year:  # 100歳以上除外
                    candidates.append((y_west, None, None))
                return candidates
        
        # S1/2/3, H1-2-3, S.51.5.1 のような年月日のパターン（ドット区切りも対応）
        match_era = re.match(r'([SHR])\.?(\d{1,2})[\.\-\/\s]?(\d{1,2})[\.\-\/\s]?(\d{1,2})?', query_upper)
        if match_era:
            era, y, m, d = match_era.groups()
            if era in ERA_OFFSETS:
                y_west = ERA_OFFSETS[era] + int(y) - 1
                if y_west >= min_year:  # 100歳以上除外
                    if d:
                        candidates.append((y_west, int(m), int(d)))
                    else:
                        candidates.append((y_west, int(m), None))
                return candidates
    except (ValueError, KeyError) as e:
        pass

    # 2. 数字のみ抽出
    try:
        nums = re.findall(r'\d+', query_norm)
        nums_joined = "".join(nums)
        if not nums_joined:
            return []
    except Exception as e:
        return []
    
    L = len(nums_joined)
    
    # 3. 全パターンを網羅的に生成
    # 年のみのパターン
    _add_year_only_patterns(nums_joined, L, candidates, min_year, current_year)
    
    # 月日のみのパターン
    _add_month_day_patterns(nums_joined, L, candidates)
    
    # 年月のパターン
    _add_year_month_patterns(nums_joined, L, candidates, min_year, current_year)
    
    # 年月日のパターン
    _add_year_month_day_patterns(nums_joined, L, candidates, min_year, current_year)
    
    # 重複を除去して返す（順序を保持）
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)
    return unique_candidates


def _add_year_only_patterns(nums, L, candidates, min_year, current_year):
    """年のみのパターンを追加"""
    try:
        # 4桁の年（西暦）
        if L == 4:
            year = int(nums)
            if min_year <= year <= current_year + 10:
                candidates.append((year, None, None))
        
        # 2桁の年（元号 + 西暦下2桁）
        if L == 2:
            year_part = int(nums)
            # 元号として解釈
            for era, offset in ERA_OFFSETS.items():
                era_year = offset + year_part - 1
                if min_year <= era_year <= current_year + 10:
                    candidates.append((era_year, None, None))
            # 西暦下2桁として解釈
            year_2000 = 2000 + year_part
            year_1900 = 1900 + year_part
            if min_year <= year_2000 <= current_year + 10:
                candidates.append((year_2000, None, None))
            if min_year <= year_1900 <= current_year + 10:
                candidates.append((year_1900, None, None))
    except (ValueError, OverflowError):
        pass


def _add_month_day_patterns(nums, L, candidates):
    """月日のみのパターンを追加"""
    try:
        # 全ての分割パターンを試す
        for i in range(1, L):
            month_str = nums[:i]
            day_str = nums[i:]
            
            # 先頭0を除去して解釈
            month = int(month_str)
            day = int(day_str)
            
            if 1 <= month <= 12 and 1 <= day <= 31:
                candidates.append((None, month, day))
    except (ValueError, OverflowError):
        pass


def _add_year_month_patterns(nums, L, candidates, min_year, current_year):
    """年月のパターンを追加"""
    try:
        # 全ての分割パターンを試す
        for i in range(1, L):
            year_str = nums[:i]
            month_str = nums[i:]
            
            month = int(month_str)
            if not (1 <= month <= 12):
                continue
            
            # 1桁の年
            if i == 1:
                year_part = int(year_str)
                # 元号として解釈
                for era, offset in ERA_OFFSETS.items():
                    era_year = offset + year_part - 1
                    if min_year <= era_year <= current_year + 10:
                        candidates.append((era_year, month, None))
                # 西暦として解釈（2001年など）
                year_2000 = 2000 + year_part
                if min_year <= year_2000 <= current_year + 10:
                    candidates.append((year_2000, month, None))
            
            # 2桁の年
            elif i == 2:
                year_part = int(year_str)
                # 元号として解釈
                for era, offset in ERA_OFFSETS.items():
                    era_year = offset + year_part - 1
                    if min_year <= era_year <= current_year + 10:
                        candidates.append((era_year, month, None))
                # 西暦下2桁として解釈
                year_2000 = 2000 + year_part
                year_1900 = 1900 + year_part
                if min_year <= year_2000 <= current_year + 10:
                    candidates.append((year_2000, month, None))
                if min_year <= year_1900 <= current_year + 10:
                    candidates.append((year_1900, month, None))
            
            # 4桁の年（西暦）
            elif i == 4:
                year = int(year_str)
                if min_year <= year <= current_year + 10:
                    candidates.append((year, month, None))
    except (ValueError, OverflowError):
        pass


def _add_year_month_day_patterns(nums, L, candidates, min_year, current_year):
    """年月日のパターンを追加"""
    try:
        # 全ての分割パターンを試す
        for i in range(1, L-1):  # 年の桁数
            for j in range(i+1, L):  # 月の終わり位置
                year_str = nums[:i]
                month_str = nums[i:j]
                day_str = nums[j:]
                
                month = int(month_str)
                day = int(day_str)
                
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    continue
                
                # 1桁の年
                if i == 1:
                    year_part = int(year_str)
                    # 0年の場合は2000年として解釈（例: 0105 → 2000年10月5日）
                    if year_part == 0:
                        if min_year <= 2000 <= current_year + 10:
                            candidates.append((2000, month, day))
                    else:
                        # 元号として解釈
                        for era, offset in ERA_OFFSETS.items():
                            era_year = offset + year_part - 1
                            if min_year <= era_year <= current_year + 10:
                                candidates.append((era_year, month, day))
                        # 西暦として解釈（2001年など）
                        year_2000 = 2000 + year_part
                        if min_year <= year_2000 <= current_year + 10:
                            candidates.append((year_2000, month, day))
                
                # 2桁の年
                elif i == 2:
                    year_part = int(year_str)
                    # 元号として解釈
                    for era, offset in ERA_OFFSETS.items():
                        era_year = offset + year_part - 1
                        if min_year <= era_year <= current_year + 10:
                            candidates.append((era_year, month, day))
                    # 西暦下2桁として解釈
                    year_2000 = 2000 + year_part
                    year_1900 = 1900 + year_part
                    if min_year <= year_2000 <= current_year + 10:
                        candidates.append((year_2000, month, day))
                    if min_year <= year_1900 <= current_year + 10:
                        candidates.append((year_1900, month, day))
                
                # 4桁の年（西暦）
                elif i == 4:
                    year = int(year_str)
                    if min_year <= year <= current_year + 10:
                        candidates.append((year, month, day))
    except (ValueError, OverflowError):
        pass


def parse_date_with_separators(query):
    """
    区切り文字がある入力から年月日を解析（S/H/Rのみ、100歳以上除外）
    漢字表記の元号にも対応（昭和63年12月31日、昭.60.5.1など）
    戻り値: (year, month, day) または None
    """
    if not query or not str(query).strip():
        return None
    
    try:
        query_norm = unicodedata.normalize('NFKC', str(query))
        current_year = datetime.datetime.now().year
        min_year = current_year - 100  # 100歳以上は除外
        
        # 漢字表記の元号を英字に変換
        query_for_parse = query_norm
        for kanji, eng in ERA_KANJI_MAP.items():
            if query_norm.startswith(kanji):
                query_for_parse = eng + query_norm[len(kanji):]
                break
        
        # 英字を大文字に統一
        query_upper = query_for_parse.upper()
        
        # 「年」「月」「日」を区切り文字として扱う
        query_upper = re.sub(r'[年月日]', '.', query_upper)
        
        # 区切り文字で分割
        parts = re.split(r'[\.\/\-\s]+', query_upper)
        parts = [p.strip() for p in parts if p.strip()]
        
        # 和暦パターンチェック（S/H/Rのみ）
        if parts and len(parts[0]) > 0 and parts[0][0] in 'SHR':
            era = parts[0][0]
            if era in ERA_OFFSETS:
                year_part = parts[0][1:] if len(parts[0]) > 1 else (parts[1] if len(parts) > 1 else None)
                if year_part and year_part.isdigit():
                    y_west = ERA_OFFSETS[era] + int(year_part) - 1
                    if y_west >= min_year:  # 100歳以上除外
                        if len(parts) >= 3:
                            m = int(parts[-2]) if parts[-2].isdigit() else None
                            d = int(parts[-1]) if parts[-1].isdigit() else None
                            if m and d and 1 <= m <= 12 and 1 <= d <= 31:
                                return (y_west, m, d)
                        elif len(parts) == 2:
                            m = int(parts[-1]) if parts[-1].isdigit() else None
                            if m and 1 <= m <= 12:
                                return (y_west, m, None)
        
        # 数字のみのパーツ
        num_parts = [p for p in parts if p.isdigit()]
        if len(num_parts) == 3:
            y, m, d = int(num_parts[0]), int(num_parts[1]), int(num_parts[2])
            if y < 100:
                y += 2000 if y < 30 else 1900
            if min_year <= y <= current_year + 10 and 1 <= m <= 12 and 1 <= d <= 31:
                return (y, m, d)
        elif len(num_parts) == 2:
            v1, v2 = int(num_parts[0]), int(num_parts[1])
            if v1 > 31:  # 年月
                if v1 < 100:
                    v1 += 2000 if v1 < 30 else 1900
                if min_year <= v1 <= current_year + 10 and 1 <= v2 <= 12:
                    return (v1, v2, None)
            else:  # 月日
                if 1 <= v1 <= 12 and 1 <= v2 <= 31:
                    return (None, v1, v2)
    except Exception as e:
        pass
    
    return None


def generate_birth_search_keys(year, month, day):
    """
    生年月日から検索用キーを生成（年・月・日を分離して格納）
    戻り値: {'year': int, 'month': int, 'day': int}
    """
    if not all([year, month, day]):
        return None
    
    try:
        if not (1800 <= year <= 2200 and 1 <= month <= 12 and 1 <= day <= 31):
            return None
        return {'year': year, 'month': month, 'day': day}
    except (TypeError, ValueError) as e:
        return None


def generate_era_candidates(year, month, day):
    """
    西暦の年月日から、元号省略形の候補を生成
    例: 1989/2/3 → H01/02/03 の場合、0123, 123, 010203 などを生成
    この関数は後方互換性のために残すが、新しい検索では使用しない
    """
    if not all([year, month, day]):
        return []
    
    try:
        candidates = []
        
        # 元号判定
        dt = datetime.datetime(year, month, day)
        era = None
        era_year = None
    except (TypeError, ValueError) as e:
        return []
    
    if dt >= datetime.datetime(2019, 5, 1):
        era = 'R'
        era_year = year - 2018
    elif dt >= datetime.datetime(1989, 1, 8):
        era = 'H'
        era_year = year - 1988
    elif dt >= datetime.datetime(1926, 12, 25):
        era = 'S'
        era_year = year - 1925
    elif dt >= datetime.datetime(1912, 7, 30):
        era = 'T'
        era_year = year - 1911
    elif dt >= datetime.datetime(1868, 1, 25):
        era = 'M'
        era_year = year - 1867
    
    try:
        if era and era_year:
            # 元号年を1桁と2桁の両方で生成
            ey_1 = str(era_year)
            ey_2 = f"{era_year:02d}"
            m_1 = str(month)
            m_2 = f"{month:02d}"
            d_1 = str(day)
            d_2 = f"{day:02d}"
            
            # 元号省略形の候補生成
            # 例: H01/02/03 → 0123, 123, 010203, 10203 など
            candidates.extend([
                ey_2 + m_2 + d_2,  # 010203
                ey_2 + m_1 + d_2,  # 0123
                ey_2 + m_2 + d_1,  # 01023
                ey_2 + m_1 + d_1,  # 0123
                ey_1 + m_2 + d_2,  # 10203
                ey_1 + m_1 + d_2,  # 123
                ey_1 + m_2 + d_1,  # 1023
                ey_1 + m_1 + d_1,  # 123
            ])
        
        # 西暦の候補も生成
        y_2 = str(year % 100)  # 下2桁
        y_4 = str(year)
        m_1 = str(month)
        m_2 = f"{month:02d}"
        d_1 = str(day)
        d_2 = f"{day:02d}"
        
        candidates.extend([
            y_4 + m_2 + d_2,  # 19890203
            y_2 + m_2 + d_2,  # 890203
            y_2 + m_1 + d_2,  # 8923
            y_2 + m_2 + d_1,  # 89023
            y_2 + m_1 + d_1,  # 8923
            m_2 + d_2,        # 0203
            m_1 + d_2,        # 23
            m_2 + d_1,        # 023
            m_1 + d_1,        # 23
        ])
    except Exception as e:
        pass
    
    return list(set(candidates))


def parse_excel_date(value):
    """Excel日付変換 (ソート用 & 表示変換用) - 強力パース版"""
    if pd.isna(value) or value == '':
        return None
    
    try:
        # 1. datetimeオブジェクトならそのまま
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        
        # 2. シリアル値判定
        val_float = None
        if isinstance(value, (int, float)):
            val_float = float(value)
        else:
            try:
                if re.match(r'^\d+(\.\d+)?$', str(value).strip()):
                    val_float = float(str(value))
            except (ValueError, AttributeError):
                pass
        
        if val_float is not None:
            if 1 <= val_float <= 100000:
                return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=val_float)

        # 3. 文字列解析 (1987.8.9, 1987/8/9, S62.8.9, 昭和60.5.1 等)
        s_raw = str(value).strip()
        s_norm = unicodedata.normalize('NFKC', s_raw)
        
        # 漢字表記の元号を英字に変換
        s_for_parse = s_norm
        for kanji, eng in ERA_KANJI_MAP.items():
            if s_norm.startswith(kanji):
                s_for_parse = eng + s_norm[len(kanji):]
                break
        
        # 英字を大文字に統一
        s_upper = s_for_parse.upper()
        
        # 「年」「月」「日」を区切り文字として扱う
        s_upper = re.sub(r'[年月日]', '.', s_upper)

        # 区切り文字 (., /, -, space) で分割して判定
        parts = re.split(r'[\.\-\/\s]+', s_upper)
        parts = [p.strip() for p in parts if p.strip()]
        
        # 和暦パターンチェック（S/H/R/M/Tのみ）
        if parts and len(parts[0]) > 0 and parts[0][0] in 'MTSHR':
            era = parts[0][0]
            if era in ERA_OFFSETS:
                year_part = parts[0][1:] if len(parts[0]) > 1 else (parts[1] if len(parts) > 1 else None)
                if year_part and year_part.isdigit():
                    year = ERA_OFFSETS[era] + int(year_part) - 1
                    if len(parts) >= 3:
                        m = int(parts[-2]) if parts[-2].isdigit() else None
                        d = int(parts[-1]) if parts[-1].isdigit() else None
                        if m and d and 1 <= m <= 12 and 1 <= d <= 31:
                            return datetime.datetime(year, m, d)
                    elif len(parts) == 2:
                        m = int(parts[-1]) if parts[-1].isdigit() else None
                        if m and 1 <= m <= 12:
                            # 月のみの場合は1日として扱う
                            return datetime.datetime(year, m, 1)
        
        # 数字のみのパーツ
        num_parts = [p for p in parts if p.isdigit()]
        if len(num_parts) == 3:
            y, m, d = int(num_parts[0]), int(num_parts[1]), int(num_parts[2])
            if y < 100:
                y += 2000 if y < 30 else 1900
            
            if 1800 <= y <= 2200 and 1 <= m <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, m, d)

        # 4. 和暦記号付きや8桁数字の解析（後方互換性のため残す）
        s_clean = re.sub(r'[−‐─━\-\(\)\.\/\s　]', '', s_upper)
        
        # 和暦判定 (S500101)
        match_era = re.match(r'([MTSHR])\W?(\d{1,2})\W?(\d{1,2})\W?(\d{1,2})', s_clean)
        if match_era:
            era, y, m, d = match_era.groups()
            if era in ERA_OFFSETS:
                year = ERA_OFFSETS[era] + int(y) - 1
                return datetime.datetime(year, int(m), int(d))
        
        # 8桁数字 (19870809)
        if len(s_clean) == 8 and s_clean.isdigit():
            y = int(s_clean[:4])
            m = int(s_clean[4:6])
            d = int(s_clean[6:])
            if 1800 <= y <= 2200 and 1 <= m <= 12 and 1 <= d <= 31:
                return datetime.datetime(y, m, d)

    except Exception as e:
        pass
    
    return None


def format_date_text(dt):
    """表示用日付文字列作成: 和暦(西暦)/月/日"""
    if pd.isna(dt):
        return ""
    
    try:
        y, m, d = dt.year, dt.month, dt.day
        era, ey = "", y
        if dt >= datetime.datetime(2019, 5, 1):
            era = "R"
            ey = y - 2018
        elif dt >= datetime.datetime(1989, 1, 8):
            era = "H"
            ey = y - 1988
        elif dt >= datetime.datetime(1926, 12, 25):
            era = "S"
            ey = y - 1925
        elif dt >= datetime.datetime(1912, 7, 30):
            era = "T"
            ey = y - 1911
        elif dt >= datetime.datetime(1868, 1, 25):
            era = "M"
            ey = y - 1867
        else:
            return dt.strftime('%Y/%m/%d')
        return f"{era}{ey}({y})/{m:02}/{d:02}"
    except (AttributeError, ValueError) as e:
        return ""
