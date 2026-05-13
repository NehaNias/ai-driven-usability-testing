import numpy as np


metric_counts = {
    "effectiveness":   5,
    "efficiency":      4,
    "learnability":    3,
    "error-proneness": 3,
    "satisfaction":    4,
    "visibility":      3,
    "flexibility":     3,
}

total = sum(metric_counts.values())
probs = np.array([v / total for v in metric_counts.values()])
entropy = -np.sum(probs * np.log2(probs + 1e-9))
max_entropy = np.log2(len(metric_counts))
normalised = entropy / max_entropy

print(f"Entropy: {entropy:.2f} bits")
print(f"Max entropy: {max_entropy:.2f} bits")
print(f"Normalised coverage score: {normalised:.2f}")