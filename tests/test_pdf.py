"""PDF 模块纯函数和辅助类测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from newspaper_pdf.pdf import BookmarkFlowable, _escape, _format_mixed_font


# ── _escape ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestEscape:
    def test_angle_brackets(self) -> None:
        assert _escape("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"

    def test_ampersand(self) -> None:
        assert _escape("a & b") == "a &amp; b"

    def test_newlines(self) -> None:
        assert _escape("line1\nline2") == "line1<br/>line2"

    def test_preserves_quotes(self) -> None:
        result = _escape('it\'s "fine"')
        assert '"' in result
        assert "'" in result

    def test_empty_string(self) -> None:
        assert _escape("") == ""

    def test_combined(self) -> None:
        result = _escape("<a>\n&")
        assert "&lt;a&gt;" in result
        assert "<br/>" in result
        assert "&amp;" in result

    def test_no_special_chars(self) -> None:
        assert _escape("hello world") == "hello world"

    def test_multiple_newlines(self) -> None:
        assert _escape("a\nb\nc") == "a<br/>b<br/>c"


# ── _format_mixed_font ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestFormatMixedFont:
    def test_chinese_only(self) -> None:
        result = _format_mixed_font("中文文本")
        assert "font" not in result

    def test_english_only(self) -> None:
        result = _format_mixed_font("hello")
        assert '<font name="TimesNewRoman">hello</font>' == result

    def test_mixed(self) -> None:
        result = _format_mixed_font("中文English中文")
        assert "中文" in result
        assert '<font name="TimesNewRoman">English</font>' in result

    def test_numbers(self) -> None:
        result = _format_mixed_font("2026年")
        assert '<font name="TimesNewRoman">2026</font>' in result
        assert "年" in result

    def test_punctuation(self) -> None:
        result = _format_mixed_font("hello, world")
        assert '<font name="TimesNewRoman">hello, world</font>' == result

    def test_empty_string(self) -> None:
        assert _format_mixed_font("") == ""

    def test_custom_fonts(self) -> None:
        result = _format_mixed_font("hello", chinese_font="SimHei", english_font="CustomFont")
        assert '<font name="CustomFont">hello</font>' == result

    def test_whitespace_only_english(self) -> None:
        result = _format_mixed_font("   ")
        # 纯空白不应该被包裹在 font 标签中
        assert result == "   "

    def test_url(self) -> None:
        result = _format_mixed_font("https://example.com")
        assert '<font name="TimesNewRoman">https://example.com</font>' == result

    def test_english_between_chinese(self) -> None:
        result = _format_mixed_font("使用HTML解析")
        assert "使用" in result
        assert "解析" in result
        assert '<font name="TimesNewRoman">HTML</font>' in result


# ── PDFExporter progress_callback ───────────────────────────────────────────


@pytest.mark.unit
class TestPDFExporterProgressCallback:
    @patch("newspaper_pdf.pdf.register_fonts", return_value={"SimHei", "SimSun"})
    def test_callback_receives_messages(self, mock_register, tmp_path: Path) -> None:
        from unittest.mock import MagicMock
        from newspaper_pdf.models import Article
        from newspaper_pdf.pdf import PDFExporter

        messages: list[str] = []
        exporter = PDFExporter(progress_callback=messages.append)

        articles = [
            Article(
                paper_name="解放军报",
                paper_date="2026-03-10",
                paper_number="01",
                section_name="要闻",
                article_index=1,
                title="测试文章",
                subtitle="",
                author="",
                paragraphs=["正文内容。"],
                source_url="https://example.com",
            ),
        ]

        # Mock 掉实际 PDF 构建，避免依赖字体文件
        with patch.object(exporter, "_build_pdf"), patch.object(
            exporter, "_build_article_story", return_value=[]
        ):
            exporter.export_articles(
                articles=articles,
                output_dir=tmp_path,
                export_individual=True,
                export_combined=True,
            )

        assert any("开始生成" in m for m in messages)
        assert any("单篇 PDF" in m for m in messages)
        assert any("合集 PDF" in m for m in messages)

    @patch("newspaper_pdf.pdf.register_fonts", return_value={"SimHei", "SimSun"})
    def test_no_callback_when_none(self, mock_register, tmp_path: Path) -> None:
        from newspaper_pdf.models import Article
        from newspaper_pdf.pdf import PDFExporter

        exporter = PDFExporter()
        articles = [
            Article(
                paper_name="解放军报",
                paper_date="2026-03-10",
                paper_number="01",
                section_name="要闻",
                article_index=1,
                title="测试文章",
                subtitle="",
                author="",
                paragraphs=["正文内容。"],
                source_url="https://example.com",
            ),
        ]

        with patch.object(exporter, "_build_pdf"), patch.object(
            exporter, "_build_article_story", return_value=[]
        ):
            # 不应抛出异常
            exporter.export_articles(
                articles=articles,
                output_dir=tmp_path,
                export_individual=True,
                export_combined=True,
            )


# ── BookmarkFlowable ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBookmarkFlowable:
    def test_wrap_returns_zero(self) -> None:
        bf = BookmarkFlowable("title", "key", 0)
        assert bf.wrap(100, 100) == (0, 0)

    def test_draw_returns_none(self) -> None:
        bf = BookmarkFlowable("title", "key", 0)
        assert bf.draw() is None

    def test_attributes(self) -> None:
        bf = BookmarkFlowable("标题", "section-01", 1)
        assert bf.bookmark_title == "标题"
        assert bf.bookmark_key == "section-01"
        assert bf.bookmark_level == 1

    def test_level_zero(self) -> None:
        bf = BookmarkFlowable("title", "key", 0)
        assert bf.bookmark_level == 0
