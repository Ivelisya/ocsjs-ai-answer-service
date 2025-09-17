#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for validate_external_answer covering multiple-choice parsing edge cases."""
import pytest

from utils import validate_external_answer


MULTI_OPTIONS = """A. 京师兵
B. 郡县兵
C. 贵族卫队
D. 边兵"""


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("京师兵", True),  # single option text for single choice not directly tested here
        ("A", True),
        ("京师兵 郡县兵 边兵", True),  # space separated texts
        ("京师兵#郡县兵#边兵", True),  # hash separated
        ("A B D", True),  # label separated by spaces
        ("A#B#D", True),
        ("ABD", True),  # compact labels
        ("A,D", True),
        ("A;B;D", True),
        ("A/ B /D", True),
        ("A|B|D", True),
        ("京师兵 郡县兵 边兵 贵族卫队", True),  # all options
        ("X", False),  # invalid label
        ("不存在", False),  # invalid text
    ],
)
def test_validate_multiple_choice(answer, expected):
    assert (
        validate_external_answer(answer, "multiple", MULTI_OPTIONS) == expected
    )


def test_single_choice_letter():
    assert validate_external_answer("A", "single", MULTI_OPTIONS) is True


def test_single_choice_text():
    assert validate_external_answer("京师兵", "single", MULTI_OPTIONS) is True


def test_single_choice_space_separated_options():
    # Options provided in one line without labels
    options_line = "第一次世界大战 清朝灭亡 第一次鸦片战争 八国联军侵华战争"
    assert validate_external_answer("第一次鸦片战争", "single", options_line) is True

    # Also tolerate answer with extra spaces
    assert validate_external_answer(" 第一次鸦片战争 ", "single", options_line) is True
