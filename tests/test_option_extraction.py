#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from utils import extract_options_from_question, validate_external_answer


def test_extract_inline_labeled():
    q = "我国古代国防从夏朝的建立开始,一直延续到()为止。 A. 第一次世界大战 B. 清朝灭亡 C. 第一次鸦片战争 D. 八国联军侵华战争"
    opts = extract_options_from_question(q)
    assert "第一次鸦片战争" in opts
    assert len(opts) >= 4


def test_extract_parentheses_style():
    q = "下列属于三原色的是（A）红色 （B）绿色 （C）蓝色 （D）白色"
    opts = extract_options_from_question(q)
    assert set(["红色", "绿色", "蓝色"]).issubset(set(opts))


def test_validate_with_auto_extraction_single():
    # options 传空，走自动提取
    q = "我国古代国防从夏朝的建立开始,一直延续到()为止。 A. 第一次世界大战 B. 清朝灭亡 C. 第一次鸦片战争 D. 八国联军侵华战争"
    assert validate_external_answer("第一次鸦片战争", "single", "", q) is True


def test_validate_with_space_chain_and_question_help():
    # options 给一个无效单词，触发自动提取
    q = "我国古代国防从夏朝的建立开始,一直延续到()为止。 第一次世界大战 清朝灭亡 第一次鸦片战争 八国联军侵华战争"
    assert validate_external_answer("清朝灭亡", "single", "dummy", q) is True


def test_validate_multiple_with_auto_extraction():
    q = "秦朝统一中国后,逐渐形成了由()组成的武装力量体制。 A. 京师兵 B. 郡县兵 C. 贵族卫队 D. 边兵"
    assert validate_external_answer("A B D", "multiple", "", q) is True
