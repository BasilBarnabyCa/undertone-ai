"""Cleanup prompt construction and output post-processing (no network)."""

from undertone import cleanup


class TestBuildMessages:
    def test_transcript_is_wrapped_not_bare(self):
        messages = cleanup._build_messages("hello there")
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "<transcript>\nhello there\n</transcript>"

    def test_includes_fewshot_examples(self):
        messages = cleanup._build_messages("x")
        # system + (user, assistant) per example + final user
        assert len(messages) == 1 + 2 * len(cleanup.EXAMPLES) + 1
        assert messages[0]["role"] == "system"
        # a dictated question stays a question in the example output
        png_example = next(a for _, a in cleanup.EXAMPLES if "PNG" in a)
        assert png_example.strip().endswith("?")


class TestPostprocess:
    def test_strips_echoed_transcript_tags(self):
        assert cleanup._postprocess("<transcript>\nHello.\n</transcript>") == "Hello."

    def test_strips_wrapping_quotes(self):
        assert cleanup._postprocess('"Hello there."') == "Hello there."
        assert cleanup._postprocess("'Hello there.'") == "Hello there."

    def test_leaves_clean_text_untouched(self):
        assert cleanup._postprocess("Is it possible to make that into a PNG?") == (
            "Is it possible to make that into a PNG?"
        )

    def test_does_not_strip_internal_quotes(self):
        assert cleanup._postprocess('He said "hi" to me.') == 'He said "hi" to me.'
