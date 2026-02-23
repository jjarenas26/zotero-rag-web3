import matplotlib.pyplot as plt
import numpy as np
import json
import os

def generate_radar():
    if not os.path.exists("assessment_results.json"):
        print("❌ No hay resultados para graficar.")
        return

    with open("assessment_results.json", "r") as f:
        stats = json.load(f)

    labels = list(stats.keys())
    values = list(stats.values())
    num_vars = len(labels)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color='blue', alpha=0.25)
    ax.plot(angles, values, color='blue', marker='o')
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    
    plt.title("Radar de Factibilidad", y=1.1)
    plt.savefig("blockchain_radar.png")
    print("✅ Gráfico 'blockchain_radar.png' generado.")
    plt.show()

if __name__ == "__main__":
    generate_radar()