import numpy as np

metric_counts = {
    "effectiveness": 9,
    "efficiency": 3,
    "learnability": 3,
    "error-proneness": 3,
    "satisfaction": 2,
    "visibility": 10,
    "flexibility": 2,
}

total = sum(metric_counts.values())
probs = np.array([v / total for v in metric_counts.values()])
entropy = -np.sum(probs * np.log2(probs + 1e-9))
max_entropy = np.log2(len(metric_counts))
normalised = entropy / max_entropy

print(f"Entropy: {entropy:.2f} bits")
print(f"Max entropy: {max_entropy:.2f} bits")
print(f"Normalised coverage score: {normalised:.2f}")