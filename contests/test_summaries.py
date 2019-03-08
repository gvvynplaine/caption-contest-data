import pandas as pd
import pytest
import numpy as np
import os
import scipy.stats

filenames = [f for f in os.listdir("summaries/") if f[0] not in {"_", "."}]
filenames = sorted(filenames)


@pytest.fixture(params=filenames)
def df(request):
    filename = request.param
    df = pd.read_csv("summaries/" + filename)
    df.filename = filename
    return df


def test_ranks(df):
    rank_score = {r: s for r, s in zip(df["rank"], df["score"])}
    ranks = np.array(sorted(list(rank_score.keys())))

    for rank, score in rank_score.items():
        if np.isnan(score):
            continue
        i = (ranks == rank).argmax()
        if i <= 2:
            continue
        better_rank = ranks[i - 1]
        assert better_rank < rank
        better_score = rank_score[better_rank]
        if np.abs(better_score - score) > 1e-2:
            assert better_score >= score


def test_columns(df):
    expected_cols = {
        "rank",
        "caption",
        "score",
        "precision",
        "count",
        "unfunny",
        "somewhat_funny",
        "funny",
        "contest",
    }
    assert expected_cols == set(df.columns) - {"target_id"}
    contest = int(df.filename[:3])
    if contest >= 587:
        assert "target_id" in set(df.columns)

    # Make sure the best caption comes first
    assert df["rank"].iloc[0] == 1
    contest = int(df.filename[:3])
    assert (df["contest"] == contest).all()


def test_counts(df):
    expected_count = df["funny"] + df["somewhat_funny"] + df["unfunny"]
    diff = np.abs(df["count"] - expected_count)
    assert diff.max() <= 3


def test_means(df):
    df.dropna(inplace=True)
    predicted_score = df["unfunny"] + 2 * df["somewhat_funny"] + 3 * df["funny"]
    predicted_score /= df["count"]

    assert df["score"].min() >= 1
    assert df["score"].max() <= 3
    if "600" in df.filename:
        hacked = df["score"] > 2.5
        assert hacked.sum() == 1
        assert df["score"][~hacked].max() < 2.1
        hacked = hacked.idxmax()
        row = df.loc[hacked]
        assert row["funny"] == 923 and row["count"] == 924

    diff = np.abs(predicted_score - df["score"])
    assert diff.median() <= 0.01
    assert diff.quantile(0.8) <= 0.02
    assert diff.quantile(0.9) <= 0.03
    assert diff.quantile(0.99) <= 0.04


def test_few_nulls(df):
    for col in df.columns:
        nulls = df[col].isnull().sum()
        if col == "caption":
            assert nulls <= 3, "Sometimes people don't submit *anything*"
        else:
            assert nulls == 0, f"{col}"


def ranks(scores):
    return scipy.stats.rankdata(-scores, method="min").astype(int)


def test_main(df):
    try:
        test_ranks(df)
    except AssertionError:
        df["rank"] = ranks(df["score"])

        test_ranks(df)
        df.to_csv("summaries/" + df.filename, index=False)
