import json
import os

class DynamicConsultant:
    def __init__(self, questions_file, results_file="assessment_results.json"):
        self.results_file = results_file
        self.pillar_scores = {}
        self.pillar_totals = {}
        self.questions = []
        
        if not os.path.exists(questions_file):
            print(f"❌ Error: No se encuentra {questions_file}")
            return

        with open(questions_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Normalización: asegurar que tratamos con una lista
                if isinstance(data, dict):
                    self.questions = data.get("questions", list(data.values())[0])
                else:
                    self.questions = data
            except Exception as e:
                print(f"❌ Error al leer el JSON: {e}")
                return

    def run(self):
        if not self.questions: return
        
        print("\n--- 🛡️ EVALUACIÓN DE FACTIBILIDAD BLOCKCHAIN ---")
        
        for q in self.questions:
            if not isinstance(q, dict): continue
            
            pillar = q.get('pillar', 'General')
            if pillar not in self.pillar_scores:
                self.pillar_scores[pillar] = 0
                self.pillar_totals[pillar] = 0

            # Pregunta al usuario
            label = f"[{pillar}] {q.get('question_es')}"
            if q.get('is_critical'): label += " (⚠️ CRÍTICO)"
            
            resp = input(f"{label} (s/n): ").lower().strip()
            
            weight = q.get('weight', 10)
            self.pillar_totals[pillar] += weight
            if resp == 's':
                self.pillar_scores[pillar] += weight

        # Calcular porcentajes y guardar
        final_stats = {p: round((self.pillar_scores[p]/self.pillar_totals[p])*100, 2) 
                       for p in self.pillar_scores if self.pillar_totals[p] > 0}

        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(final_stats, f, indent=4)
        
        print(f"\n✅ Resultados guardados en {self.results_file}")

if __name__ == "__main__":
    DynamicConsultant("assessment_questions.json").run()