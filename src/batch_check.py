import pandas as pd

psp_data = pd.read_csv('../data/payment_data.csv')
best_lookup = (
    psp_data.sort_values('success_rate', ascending=False)
    .groupby(['country','payment_method'])['psp']
    .first()
    .to_dict()
)

df = pd.read_csv('decision_log.csv')
df['best_psp'] = df.apply(lambda r: best_lookup.get((r['country'], r['payment_method'])), axis=1)
df['is_optimal'] = df['selected_psp'] == df['best_psp']
df['batch'] = df.index // 100

print(df.groupby('batch')['is_optimal'].mean().round(3))
