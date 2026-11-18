"""Integrate symmetric label errors over anonymous counts of paired differences."""
from math import fsum


def success_probabilities(max_differences, error=0.10):
    """Expected correct fraction for two static equiprobable states, ties split.

    Passing from 2j to 2j+1 differing sites changes the expected fraction
    only on a tie after 2j sites. Adding a site after an odd count leaves the
    expectation unchanged. The central binomial mass is updated recursively.
    """
    if not 0 <= error <= 0.5:
        raise ValueError("Expected a symmetric error probability between 0 and 0.5")
    correct = 0.5
    tie_mass = 1.0
    probabilities = [correct]
    for count in range(1, max_differences + 1):
        if count % 2:
            correct = min(1.0, correct + (0.5 - error) * tie_mass)
        else:
            j = count // 2
            tie_mass *= (4 - 2 / j) * error * (1 - error)
        probabilities.append(correct)
    return probabilities


def channel_summary(histogram, correct):
    """Take only a cohort histogram. No identifiers or individual labels are inputs."""
    wallets = sum(histogram)
    if not wallets or len(correct) < len(histogram):
        raise ValueError("Expected a nonempty cohort and a complete probability table")
    distinguishable = wallets - histogram[0]
    tail_mass = fsum(n * p for n, p in zip(histogram[9:], correct[9:]))
    return dict(
        distinguishable_wallets=distinguishable,
        distinguishable_fraction=distinguishable / wallets,
        accuracy_noiseless=(wallets + distinguishable) / (2 * wallets),
        accuracy_10pct=fsum(n * p for n, p in zip(histogram, correct)) / wallets,
        different_decisions=sum(k * n for k, n in enumerate(histogram)),
        count_0=histogram[0], count_1_2=sum(histogram[1:3]),
        count_3_4=sum(histogram[3:5]), count_5_6=sum(histogram[5:7]),
        count_7_8=sum(histogram[7:9]), count_9_plus=sum(histogram[9:]),
        expected_correct_10pct_in_9_plus=tail_mass,
    )
