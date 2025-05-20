import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np  

# -------------------------------------------------
# 1) Data  (ringnummer, Δθ [°])
# -------------------------------------------------
data = [
    (1, 53.64), (1, 54.76), (1, 54.80),                        
    (2, 53.22), (2, 54.05), (2, 54.24),                       
    (3, 55.92), (3, 53.68),            
    (4, 53.89), (4, 54.00),            
    (5, 54.69), (5, 54.87),            
    (6, 53.93), (6, 54.26), (6, 54.33),                        
    (7, 55.68), (7, 54.96), (7, 55.14),            
    (8, 54.17), (8, 55.77), (8, 55.75),                              
    (9, 55.51), (9, 55.55),                              
    (10, 53.99), (10, 54.21),                            
    (29, 53.98), (29, 54.00), (29, 55.04), (29, 54.63),  
    (30, 53.00), (30, 54.22),                                        
    (33, 52.58), (33, 53.46),                                        
]

# -------------------------------------------------
# 2) Lag kompakt x-akse uten hull (1, 2, 3 …)
# -------------------------------------------------
rings_sorted = sorted({r for r, _ in data})
x_map = {ring: idx + 1 for idx, ring in enumerate(rings_sorted)}

# -------------------------------------------------
# 3) Forbered x-, y- og etikettlister
# -------------------------------------------------
x_vals, y_vals, labels = [], [], []
round_counter: defaultdict[int, int] = defaultdict(int)
ring_groups: defaultdict[int, list[float]] = defaultdict(list)

for ring, dtheta in data:
    round_counter[ring] += 1
    x_vals.append(x_map[ring])
    y_vals.append(dtheta)
    labels.append(str(round_counter[ring]))
    ring_groups[ring].append(dtheta)


# -------------------------------------------------
# 4) Gjennomsnitt per ring med NumPy
# -------------------------------------------------
avg_x = [x_map[ring] for ring in ring_groups]
avg_y = [np.mean(vals) for vals in ring_groups.values()]


# -------------------------------------------------
# 5) Plot
# -------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

# Enkeltmålinger
ax.scatter(x_vals, y_vals, color="#1f77b4", marker="o",
           label="Enkeltmålinger")

# Gjennomsnitt 
ax.scatter(
    avg_x,
    avg_y,
    color="#cc6666",   # lys/«svak» rødfarge
    marker="x",
    s=50,              # størrelsen på krysset (↓ fra 80)
    linewidths=1.5,    # litt tynnere streker
    alpha=0.85,        # ørlite gjennomsiktighet
    zorder=3,
    label="Gjennomsnitt",
)

# Runde-numrene
for x_pt, y_pt, txt in zip(x_vals, y_vals, labels):
    ax.annotate(txt, (x_pt, y_pt),
                textcoords="offset points", xytext=(4, -6),
                fontsize=8)

ax.set_xlabel("Ringnummer")
ax.set_ylabel(r"$\Delta \theta$ [°]")
ax.set_title("Visualisering av resultater – utslagsvinkel")
ax.set_xticks(list(x_map.values()))
ax.set_xticklabels([str(r) for r in rings_sorted])
ax.legend(loc="upper right")
ax.grid(True)
plt.tight_layout()
plt.show()