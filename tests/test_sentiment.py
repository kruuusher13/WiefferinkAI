"""
Tests for Gemini-Native Sentiment Extraction

The GarageAI system uses prompt-based sentiment extraction where Gemini
includes a [[SENTIMENT: emoji]] tag in its responses. These tests verify
the regex pattern extraction logic used in bridge/telephony.py.
"""

import re
import pytest


# Import the patterns from telephony (the actual implementation)
# These are the same patterns defined in bridge/telephony.py
SENTIMENT_PATTERN = re.compile(r"\[\[SENTIMENT:\s*(.+?)\]\]")
THOUGHT_PATTERN = re.compile(r"\[\[THOUGHT:.*?\]\]", re.DOTALL)


class TestSentimentPatternExtraction:
    """Test the regex pattern for extracting sentiment emojis from Gemini responses."""

    def test_extract_happy_emoji(self):
        """Test extracting happy emoji from response."""
        text = "[[SENTIMENT: 🙂]]Hallo, hoe kan ik u helpen?"
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "🙂"

    def test_extract_neutral_emoji(self):
        """Test extracting neutral emoji from response."""
        text = "[[SENTIMENT: 😐]]Ik begrijp het."
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "😐"

    def test_extract_angry_emoji(self):
        """Test extracting angry/frustrated emoji from response."""
        text = "[[SENTIMENT: 😠]]Ik begrijp dat dit frustrerend is."
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "😠"

    def test_extract_sad_emoji(self):
        """Test extracting sad emoji from response."""
        text = "[[SENTIMENT: 😢]]Dat spijt me te horen."
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "😢"

    def test_extract_with_space_after_colon(self):
        """Test extraction works with varying whitespace."""
        text = "[[SENTIMENT:  🙂]]Test"
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "🙂"

    def test_no_sentiment_returns_none(self):
        """Test that missing sentiment tag returns no match."""
        text = "Hallo, welkom bij Garage Wiefferink."
        match = SENTIMENT_PATTERN.search(text)
        assert match is None

    def test_sentiment_in_middle_of_text(self):
        """Test extracting sentiment when not at the start."""
        text = "Some prefix [[SENTIMENT: 🙂]] and more text"
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "🙂"


class TestSentimentTagStripping:
    """Test that sentiment tags are properly stripped from responses."""

    def test_strip_sentiment_tag(self):
        """Test stripping sentiment tag from text."""
        text = "[[SENTIMENT: 🙂]]Hallo, hoe kan ik u helpen?"
        clean = SENTIMENT_PATTERN.sub("", text)
        assert clean == "Hallo, hoe kan ik u helpen?"

    def test_strip_preserves_surrounding_text(self):
        """Test that stripping preserves text around the tag."""
        text = "Prefix [[SENTIMENT: 😐]] Suffix"
        clean = SENTIMENT_PATTERN.sub("", text)
        assert clean == "Prefix  Suffix"

    def test_strip_multiple_sentiment_tags(self):
        """Test stripping multiple sentiment tags (edge case)."""
        text = "[[SENTIMENT: 🙂]]Hello [[SENTIMENT: 😐]]World"
        clean = SENTIMENT_PATTERN.sub("", text)
        assert clean == "Hello World"


class TestThoughtPatternExtraction:
    """Test the regex pattern for extracting/stripping thought tags."""

    def test_strip_thought_tag(self):
        """Test stripping thought tag from text."""
        text = "[[THOUGHT: I should check the database.]]De afspraak is morgen."
        clean = THOUGHT_PATTERN.sub("", text)
        assert clean == "De afspraak is morgen."

    def test_strip_multiline_thought(self):
        """Test stripping multiline thought tag."""
        text = "[[THOUGHT: First I think this.\nThen I think that.]]Response here."
        clean = THOUGHT_PATTERN.sub("", text)
        assert clean == "Response here."

    def test_no_thought_returns_original(self):
        """Test that text without thought tag is unchanged."""
        text = "Just a normal response."
        clean = THOUGHT_PATTERN.sub("", text)
        assert clean == "Just a normal response."


class TestCombinedTagHandling:
    """Test handling both sentiment and thought tags together."""

    def test_extract_and_strip_both_tags(self):
        """Test extracting sentiment and stripping both tags."""
        text = "[[SENTIMENT: 🙂]][[THOUGHT: User seems friendly.]]Hallo!"

        # Extract sentiment
        match = SENTIMENT_PATTERN.search(text)
        assert match is not None
        sentiment = match.group(1)
        assert sentiment == "🙂"

        # Strip both tags
        clean = SENTIMENT_PATTERN.sub("", text)
        clean = THOUGHT_PATTERN.sub("", clean)
        assert clean == "Hallo!"

    def test_realistic_gemini_response(self):
        """Test with a realistic Gemini response format."""
        text = """[[SENTIMENT: 😐]][[THOUGHT: The customer is asking about their appointment. Let me check the system.]]Ik zie dat uw afspraak gepland staat voor morgen om 10:00 uur."""

        # Extract sentiment
        match = SENTIMENT_PATTERN.search(text)
        sentiment = match.group(1) if match else "😐"
        assert sentiment == "😐"

        # Clean the text
        clean = SENTIMENT_PATTERN.sub("", text)
        clean = THOUGHT_PATTERN.sub("", clean)
        assert clean == "Ik zie dat uw afspraak gepland staat voor morgen om 10:00 uur."
