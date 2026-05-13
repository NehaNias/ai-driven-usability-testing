def gwets_ac1(r1, r2, categories=None):
    if categories is None:
        categories = list(range(1, 6)) 
    n = len(r1)
    
    
    observed = sum(1 for a, b in zip(r1, r2) if a == b) / n
    
    # Expected agreement (Gwet's formula)
    category_props = []
    for k in categories:
        pk = (r1.count(k) + r2.count(k)) / (2 * n)
        category_props.append(pk * (1 - pk))
    
    chance = sum(category_props) / (len(categories) - 1)
    
    if chance == 1:
        return 1.0
    return (observed - chance) / (1 - chance)

your_realism    = [4, 3, 5, 4, 5, 4, 5, 5, 4, 4, 3, 3, 5, 5, 4]
rater2_realism  = [4, 5, 5, 4, 5, 5, 5, 5, 5, 3, 5, 4, 5, 5, 4]

your_clarity    = [5, 5, 5, 4, 5, 5, 5, 5, 4, 4, 5, 5, 5, 5, 5]
rater2_clarity  = [5, 5, 4, 5, 5, 5, 4, 5, 5, 4, 5, 4, 5, 5, 5]


your_independence = [5, 4, 4, 4, 5, 4, 5, 5, 4, 5, 5, 4, 5, 5, 5]
rater2_independence = [5, 5, 5, 3, 4, 5, 5, 5, 4, 4, 5, 4, 5, 5, 5]

your_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 4]
rater2_measurability = [5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5]

print(f"Realism:       {gwets_ac1(your_realism, rater2_realism):.2f}")
print(f"Clarity:       {gwets_ac1(your_clarity, rater2_clarity):.2f}")
print(f"Independence:  {gwets_ac1(your_independence, rater2_independence):.2f}")
print(f"Measurability: {gwets_ac1(your_measurability, rater2_measurability):.2f}")