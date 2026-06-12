"""Tests for core response formatting utilities."""

from champi_stt.core.response import (
    STTResponse,
    TranscriptionResponse,
    TranscriptionSegment,
    create_error_response,
    format_response,
    format_segment,
    format_verbose_json,
    standardize_provider_response,
)


class TestTranscriptionSegment:
    def test_defaults(self):
        seg = TranscriptionSegment()
        assert seg.id == 0
        assert seg.text == ""
        assert seg.start == 0.0
        assert seg.end == 0.0
        assert seg.tokens == []

    def test_custom(self):
        seg = TranscriptionSegment(id=1, start=1.0, end=2.5, text="hello")
        assert seg.id == 1
        assert seg.text == "hello"


class TestTranscriptionResponse:
    def test_defaults(self):
        resp = TranscriptionResponse()
        assert resp.text == ""
        assert resp.language == "unknown"
        assert resp.segments == []
        assert resp.task == "transcribe"

    def test_stt_response_alias(self):
        assert STTResponse is TranscriptionResponse


class TestFormatResponse:
    def test_json_format(self):
        result = format_response({"text": "hello"}, "json")
        assert result == {"text": "hello"}

    def test_text_format(self):
        result = format_response({"text": "hello world"}, "text")
        assert result == "hello world"

    def test_verbose_json_format(self):
        result = format_response(
            {"text": "hi", "language": "en", "duration": 1.0}, "verbose_json"
        )
        assert isinstance(result, dict)
        assert result["text"] == "hi"
        assert result["language"] == "en"

    def test_unknown_format_returns_raw(self):
        raw = {"text": "hi", "extra": "data"}
        result = format_response(raw, "unknown_format")
        assert result == raw

    def test_json_missing_text(self):
        result = format_response({}, "json")
        assert result == {"text": ""}


class TestFormatVerboseJson:
    def test_basic(self):
        result = format_verbose_json({"text": "hi", "language": "en", "duration": 2.0})
        assert result["text"] == "hi"
        assert result["language"] == "en"
        assert result["duration"] == 2.0

    def test_optional_fields(self):
        result = format_verbose_json(
            {
                "text": "hi",
                "language": "en",
                "duration": 1.0,
                "task": "transcribe",
                "language_probability": 0.95,
                "duration_after_vad": 0.8,
                "processing_time": 0.5,
            }
        )
        assert result["task"] == "transcribe"
        assert result["language_probability"] == 0.95
        assert result["duration_after_vad"] == 0.8
        assert result["processing_time"] == 0.5

    def test_with_segments(self):
        result = format_verbose_json(
            {
                "text": "hi",
                "language": "en",
                "duration": 1.0,
                "segments": [{"id": 0, "start": 0.0, "end": 0.5, "text": "hi"}],
            }
        )
        assert len(result["segments"]) == 1
        assert result["segments"][0]["text"] == "hi"


class TestFormatSegment:
    def test_basic_fields(self):
        seg = {"id": 1, "start": 0.5, "end": 1.0, "text": "world"}
        result = format_segment(seg)
        assert result["id"] == 1
        assert result["start"] == 0.5
        assert result["text"] == "world"

    def test_optional_fields(self):
        seg = {
            "id": 0,
            "start": 0.0,
            "end": 0.5,
            "text": "hi",
            "tokens": [1, 2],
            "temperature": 0.0,
            "avg_logprob": -0.1,
            "compression_ratio": 1.2,
            "no_speech_prob": 0.01,
            "seek": 0,
        }
        result = format_segment(seg)
        assert result["tokens"] == [1, 2]
        assert result["no_speech_prob"] == 0.01

    def test_missing_fields_use_defaults(self):
        result = format_segment({})
        assert result["id"] == 0
        assert result["text"] == ""


class TestStandardizeProviderResponse:
    def test_whisperlive_passthrough(self):
        data = {"text": "hi", "language": "en"}
        result = standardize_provider_response(data, "whisperlive")
        assert result is data

    def test_openai_dict(self):
        result = standardize_provider_response(
            {"text": "hi", "language": "en", "duration": 1.0}, "openai"
        )
        assert result["text"] == "hi"

    def test_string_input(self):
        result = standardize_provider_response("hello", "unknown")
        assert result == {"text": "hello"}

    def test_dict_passthrough(self):
        data = {"text": "hi"}
        result = standardize_provider_response(data, "custom")
        assert result is data

    def test_other_type(self):
        result = standardize_provider_response(42, "custom")
        assert result == {"text": "42"}


class TestCreateErrorResponse:
    def test_error_response(self):
        err = ValueError("bad input")
        result = create_error_response(err)
        assert result["error"] is True
        assert result["error_type"] == "ValueError"
        assert result["error_message"] == "bad input"
        assert result["text"] == ""
