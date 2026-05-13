from sklearn.metrics import cohen_kappa_score
import numpy as np

your_realism    = [4, 3, 5, 4, 5, 4, 5, 5, 4, 4, 3, 3, 5, 5, 4]
rater2_realism  = [4, 5, 5, 4, 5, 5, 5, 5, 5, 3, 5, 4, 5, 5, 4]

your_clarity    = [5, 5, 5, 4, 5, 5, 5, 5, 4, 4, 5, 5, 5, 5, 5]
rater2_clarity  = [5, 5, 4, 5, 5, 5, 4, 5, 5, 4, 5, 4, 5, 5, 5]


your_independence = [5, 4, 4, 4, 5, 4, 5, 5, 4, 5, 5, 4, 5, 5, 5]
rater2_independence = [5, 5, 5, 3, 4, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5]

your_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 4]
rater2_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5]

kappa_realism  = cohen_kappa_score(your_realism, rater2_realism, weights='linear')
kappa_clarity  = cohen_kappa_score(your_clarity, rater2_clarity, weights='linear')
kappa_independence = cohen_kappa_score(your_independence, rater2_independence, weights='linear')
kappa_measurability = cohen_kappa_score(your_measurability, rater2_measurability, weights='linear')

print(f"Kappa realism:  {kappa_realism:.2f}")
print(f"Kappa clarity:  {kappa_clarity:.2f}")
print(f"Kappa independence:  {kappa_independence:.2f}")
print(f"Kappa measurability:  {kappa_measurability:.2f}")





