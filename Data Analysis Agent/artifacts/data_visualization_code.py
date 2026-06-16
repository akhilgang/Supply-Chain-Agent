import os
import matplotlib.pyplot as plt
from datetime import datetime

os.makedirs('artifacts', exist_ok=True)

original_dates = [
    '2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04', '2025-09-05', '2025-09-06', '2025-09-07', '2025-09-08',
    '2025-09-09', '2025-09-10', '2025-09-11', '2025-09-12', '2025-09-13', '2025-09-14', '2025-09-15', '2025-09-16',
    '2025-09-17', '2025-09-18', '2025-09-19', '2025-09-20'
]
original_visits = [
    542, 489, 563, 512, 0, 598, 621, 505,
    0, 534, 511, 490, 523, 514, 2500, 527,
    499, 5545, 488, 531
]

cleaned_dates = [
    '2025-09-01', '2025-09-02', '2025-09-03', '2025-09-04',
    '2025-09-06', '2025-09-07', '2025-09-08',
    '2025-09-10', '2025-09-11', '2025-09-12',
    '2025-09-13', '2025-09-14', '2025-09-16',
    '2025-09-17', '2025-09-19', '2025-09-20'
]
cleaned_visits = [
    542, 489, 563, 512,
    598, 621, 505,
    534, 511, 490,
    523, 514, 527,
    499, 488, 531
]

original_dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in original_dates]
cleaned_dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in cleaned_dates]

plt.figure(figsize=(12,6))
plt.plot(original_dates_dt, original_visits, color='blue', label='Original', linewidth=2)
plt.plot(cleaned_dates_dt, cleaned_visits, color='green', label='Cleaned', linewidth=2)

plt.title("Website Visits: Original vs Cleaned Data")
plt.xlabel("Date")
plt.ylabel("Website Visits")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('artifacts/data_visualization.png')