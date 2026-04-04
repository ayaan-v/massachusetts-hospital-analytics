# US Hospital Analytics — Python EDA

import pandas as pd
import numpy as np

# ── Load data ─────────────────────────────────────────────────────────────────
print('Loading data...')

encounters = pd.read_csv('Dataset/encounters.csv')
patients   = pd.read_csv('Dataset/patients.csv')
payers     = pd.read_csv('Dataset/payers.csv')
procedures = pd.read_csv('Dataset/procedures.csv')

encounters.columns = encounters.columns.str.strip()
patients.columns   = patients.columns.str.strip()
payers.columns     = payers.columns.str.strip()
procedures.columns = procedures.columns.str.strip()

print('Data loaded!')
print()

# Date parsing 
encounters['START']   = pd.to_datetime(encounters['START'], utc=True)
encounters['STOP']    = pd.to_datetime(encounters['STOP'],  utc=True)
procedures['START']   = pd.to_datetime(procedures['START'], utc=True)
patients['BIRTHDATE'] = pd.to_datetime(patients['BIRTHDATE'])

# Derived columns 
encounters['Year']           = encounters['START'].dt.year
encounters['Month']          = encounters['START'].dt.month
encounters['Quarter']        = encounters['START'].dt.to_period('Q').astype(str)
encounters['Duration_Hours'] = (encounters['STOP'] - encounters['START']).dt.total_seconds() / 3600
encounters['Zero_Coverage']  = encounters['PAYER_COVERAGE'] == 0

payer_names = payers[['Id', 'NAME']].rename(columns={'Id': 'PAYER', 'NAME': 'PAYER_NAME'})
encounters  = encounters.merge(payer_names, on='PAYER', how='left')

patients['Age'] = np.floor(
    (pd.Timestamp.now() - patients['BIRTHDATE']).dt.days / 365
).astype(int)

print(f'Encounters : {len(encounters):,}')
print(f'Patients   : {len(patients):,}')
print(f'Procedures : {len(procedures):,}')
print(f'Payers     : {len(payers):,}')
print(f'Date range : {encounters["START"].min().date()}  to  {encounters["START"].max().date()}')
print()



# SECTION 1 — 30-DAY READMISSION ANALYSIS

print('SECTION 1 — 30-Day Readmission Analysis')

enc_sorted = (
    encounters[['Id', 'PATIENT', 'START', 'STOP']]
    .sort_values(['PATIENT', 'START'])
    .copy()
)

enc_sorted['Prev_Stop']       = enc_sorted.groupby('PATIENT')['STOP'].shift(1)
enc_sorted['Days_Since_Last'] = (
    enc_sorted['START'] - enc_sorted['Prev_Stop']
).dt.total_seconds() / 86400

readmit = enc_sorted[
    (enc_sorted['Days_Since_Last'] >= 0) &
    (enc_sorted['Days_Since_Last'] <= 30)
]

readmit_patients = readmit['PATIENT'].nunique()
total_patients   = encounters['PATIENT'].nunique()
readmit_pct      = round(readmit_patients / total_patients * 100, 1)

print(f'Total unique patients              : {total_patients:,}')
print(f'Patients readmitted within 30 days : {readmit_patients:,}')
print(f'30-day readmission rate            : {readmit_pct}%')
print()

# Readmission count distribution
readmit_count = (
    readmit.groupby('PATIENT')
    .size()
    .reset_index(name='Readmissions')
)

readmit_dist = (
    readmit_count['Readmissions']
    .value_counts()
    .sort_index()
    .reset_index()
)
readmit_dist.columns = ['Readmission_Count', 'Patients']

print('Readmission Count Distribution:')
print(readmit_dist.to_string(index=False))
print()

# Top 10 most readmitted patients
top_readmit = (
    readmit_count
    .sort_values('Readmissions', ascending=False)
    .head(10)
    .reset_index(drop=True)
)
top_readmit.index += 1
print('Top 10 Most Readmitted Patients:')
print(top_readmit.to_string())
print()

# Average days between encounters for readmitted patients
avg_days_between = round(readmit['Days_Since_Last'].mean(), 1)
print(f'Avg days between encounters (readmitted patients) : {avg_days_between}')
print()


# SECTION 2 — PATIENT DEMOGRAPHICS DEEP DIVE

print('SECTION 2 — Patient Demographics Deep Dive')


pat_age = patients[patients['Age'].between(0, 100)].copy()

def age_group(age):
    if age < 18:   return '0-17  (Child)'
    elif age < 35: return '18-34 (Young Adult)'
    elif age < 50: return '35-49 (Middle Adult)'
    elif age < 65: return '50-64 (Older Adult)'
    else:          return '65+   (Senior)'

pat_age['Age_Group'] = pat_age['Age'].apply(age_group)

# Age group distribution
age_dist = (
    pat_age['Age_Group']
    .value_counts()
    .sort_index()
    .reset_index()
)
age_dist.columns = ['Age_Group', 'Count']
age_dist['Percent'] = round(age_dist['Count'] / age_dist['Count'].sum() * 100, 1)

print('Age Group Distribution:')
print(age_dist.to_string(index=False))
print()

# Age group + gender breakdown
age_gender = (
    pat_age.groupby(['Age_Group', 'GENDER'])
    .size()
    .reset_index(name='Count')
)
age_gender['GENDER'] = age_gender['GENDER'].map({'M': 'Male', 'F': 'Female'})
age_gender.columns   = ['Age_Group', 'Gender', 'Count']

print('Age Group by Gender:')
print(age_gender.to_string(index=False))
print()

# Age group + race breakdown
age_race = (
    pat_age.groupby(['Age_Group', 'RACE'])
    .size()
    .reset_index(name='Count')
    .sort_values(['Age_Group', 'Count'], ascending=[True, False])
)
print('Age Group by Race:')
print(age_race.to_string(index=False))
print()

# Key age stats
ages = pat_age['Age'].values
print('Age Statistics:')
print(f'  Mean   : {np.mean(ages):.1f}')
print(f'  Median : {np.median(ages):.0f}')
print(f'  Std Dev: {np.std(ages):.1f}')
print(f'  Min    : {np.min(ages)}')
print(f'  Max    : {np.max(ages)}')
print()

# Marital status
marital = (
    pat_age['MARITAL']
    .value_counts()
    .reset_index()
)
marital.columns = ['Marital_Status', 'Count']
marital['Marital_Status'] = marital['Marital_Status'].map({'M': 'Married', 'S': 'Single'})
marital['Percent'] = round(marital['Count'] / marital['Count'].sum() * 100, 1)
print('Marital Status:')
print(marital.to_string(index=False))
print()


# SECTION 3 — QUARTERLY PATIENT TREND

print('SECTION 3 — Quarterly Patient Trend')

pat_by_qtr = (
    encounters.groupby('Quarter')['PATIENT']
    .nunique()
    .reset_index(name='Unique_Patients')
)

print('Unique Patients per Quarter:')
print(pat_by_qtr.to_string(index=False))
print()

qtr_vals = pat_by_qtr['Unique_Patients'].values
max_qtr  = pat_by_qtr.loc[pat_by_qtr['Unique_Patients'].idxmax()]
min_qtr  = pat_by_qtr.loc[pat_by_qtr['Unique_Patients'].idxmin()]

print(f'Average unique patients per quarter : {np.mean(qtr_vals):.1f}')
print(f'Highest quarter : {max_qtr["Quarter"]}  —  {max_qtr["Unique_Patients"]} patients')
print(f'Lowest quarter  : {min_qtr["Quarter"]}  —  {min_qtr["Unique_Patients"]} patients')
print()


# SECTION 4 — COST DISTRIBUTION & CORRELATION

print('SECTION 4 — Cost Distribution & Correlation')


# Claim cost percentile breakdown
claim = encounters['TOTAL_CLAIM_COST']
percentiles = [10, 25, 50, 75, 90, 95, 99]
print('Total Claim Cost — Percentile Breakdown:')
for p in percentiles:
    print(f'  {p:>3}th percentile : ${np.percentile(claim, p):>10,.2f}')
print(f'  {"Mean":>14} : ${claim.mean():>10,.2f}')
print(f'  {"Std Dev":>14} : ${claim.std():>10,.2f}')
print()

# Median claim cost by encounter class
cost_by_class = (
    encounters.groupby('ENCOUNTERCLASS')['TOTAL_CLAIM_COST']
    .agg(
        Encounters='count',
        Mean_Cost='mean',
        Median_Cost='median',
        Std_Dev='std'
    )
    .round(2)
    .sort_values('Median_Cost', ascending=False)
    .reset_index()
)
cost_by_class.columns = ['Encounter_Class', 'Encounters', 'Mean_Cost', 'Median_Cost', 'Std_Dev']
print('Claim Cost by Encounter Class:')
print(cost_by_class.to_string(index=False))
print()

# Payer coverage rate analysis
coverage_by_payer = (
    encounters.groupby('PAYER_NAME')
    .apply(lambda x: pd.Series({
        'Encounters'     : len(x),
        'Avg_Claim_Cost' : round(x['TOTAL_CLAIM_COST'].mean(), 2),
        'Avg_Coverage'   : round(x['PAYER_COVERAGE'].mean(), 2),
        'Coverage_Rate'  : round(
            x['PAYER_COVERAGE'].sum() / x['TOTAL_CLAIM_COST'].sum() * 100, 1
        ) if x['TOTAL_CLAIM_COST'].sum() > 0 else 0
    }))
    .sort_values('Coverage_Rate', ascending=False)
    .reset_index()
)
print('Payer Coverage Rate Analysis:')
print(coverage_by_payer.to_string(index=False))
print()

# Correlation matrix
corr_cols = ['BASE_ENCOUNTER_COST', 'TOTAL_CLAIM_COST', 'PAYER_COVERAGE', 'Duration_Hours']
corr_labels = {
    'BASE_ENCOUNTER_COST' : 'Base_Cost',
    'TOTAL_CLAIM_COST'    : 'Total_Claim',
    'PAYER_COVERAGE'      : 'Payer_Coverage',
    'Duration_Hours'      : 'Duration_Hrs'
}
corr_df = encounters[corr_cols].rename(columns=corr_labels).corr().round(3)
print('Correlation Matrix — Cost & Duration Variables:')
print(corr_df.to_string())
print()


# SECTION 5 — PROCEDURE COST ANALYSIS


print('SECTION 5 — Procedure Cost Analysis')

# Top 10 by avg base cost
top_cost_proc = (
    procedures.groupby('DESCRIPTION')
    .agg(
        Times_Performed=('CODE', 'count'),
        Avg_Base_Cost=('BASE_COST', 'mean'),
        Total_Cost=('BASE_COST', 'sum')
    )
    .round(2)
    .sort_values('Avg_Base_Cost', ascending=False)
    .head(10)
    .reset_index()
)
top_cost_proc.index += 1
print('Top 10 Procedures by Avg Base Cost:')
print(top_cost_proc.to_string())
print()

# Procedure cost percentile breakdown
proc_cost = procedures['BASE_COST']
print('Procedure Base Cost — Percentile Breakdown:')
for p in percentiles:
    print(f'  {p:>3}th percentile : ${np.percentile(proc_cost, p):>10,.2f}')
print(f'  {"Mean":>14} : ${proc_cost.mean():>10,.2f}')
print()


print('Python EDA complete.')