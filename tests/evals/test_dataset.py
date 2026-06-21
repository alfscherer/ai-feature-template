from pathlib import Path

from evals.dataset import load_dataset


def test_loads_at_least_twenty_examples() -> None:
    examples = load_dataset()

    assert len(examples) >= 20


def test_all_ids_are_unique() -> None:
    examples = load_dataset()

    ids = [e.id for e in examples]
    assert len(ids) == len(set(ids))


def test_ambiguous_examples_have_no_expected_sentiment() -> None:
    examples = {e.id: e for e in load_dataset()}

    assert examples["ambiguous-1"].expected_sentiment is None


def test_clear_cut_examples_have_expected_labels() -> None:
    examples = {e.id: e for e in load_dataset()}

    positive = examples["pos-1"]
    assert positive.expected_sentiment == "positive"
    assert positive.expected_category == "praise"
    assert positive.expected_urgency == "low"


def test_dataset_covers_required_categories() -> None:
    examples = load_dataset()
    all_tags = {tag for e in examples for tag in e.tags}

    required = {
        "positive",
        "negative",
        "ambiguous",
        "sarcasm",
        "short",
        "long",
        "multilingual",
        "contradictory",
        "security",
        "malformed",
    }
    assert required.issubset(all_tags)


def test_load_dataset_skips_blank_lines(tmp_path: Path) -> None:
    dataset_file = tmp_path / "dataset.jsonl"
    dataset_file.write_text(
        '{"id": "a", "feedback": "hi"}\n\n{"id": "b", "feedback": "bye"}\n',
        encoding="utf-8",
    )

    examples = load_dataset(dataset_file)

    assert [e.id for e in examples] == ["a", "b"]
