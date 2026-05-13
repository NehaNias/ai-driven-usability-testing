

def percent_agreement(r1, r2, tolerance=1):
    matches = sum(1 for a, b in zip(r1, r2) if abs(a - b) <= tolerance)
    return round(matches / len(r1) * 100, 1)



your_realism    = [4, 3, 5, 4, 5, 4, 5, 5, 4, 4, 3, 3, 5, 5, 4]
rater2_realism  = [4, 5, 5, 4, 5, 5, 5, 5, 5, 3, 5, 4, 5, 5, 4]

your_clarity    = [5, 5, 5, 4, 5, 5, 5, 5, 4, 4, 5, 5, 5, 5, 5]
rater2_clarity  = [5, 5, 4, 5, 5, 5, 4, 5, 5, 4, 5, 4, 5, 5, 5]


your_independence = [5, 4, 4, 4, 5, 4, 5, 5, 4, 5, 5, 4, 5, 5, 5]
rater2_independence = [5, 5, 5, 3, 4, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5]

your_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 4]
rater2_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5]

print(f"Realism:       {percent_agreement(your_realism, rater2_realism)}%")
print(f"Clarity:       {percent_agreement(your_clarity, rater2_clarity)}%")
print(f"Independence:  {percent_agreement(your_independence, rater2_independence)}%")
print(f"Measurability: {percent_agreement(your_measurability, rater2_measurability)}%")

