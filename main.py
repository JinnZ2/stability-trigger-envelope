# main.py

from dashboard.dashboard import NoiseDashboard
from symbolic.symbolic_intelligence import SymbolicIntelligenceEngine

# Simulated raw input data
raw_sensor_data = {
    'molecular': [0.98, 0.95, 1.01, 0.97, 0.99],
    'chemical': [0.88, 0.85, 0.83, 0.87, 0.89],
    'motion': [0.67, 0.7, 0.72, 0.71, 0.69],
    'atmospheric': [0.61, 0.65, 0.63, 0.6, 0.62]
}

if __name__ == "__main__":
    # Step 1: Core noise fusion
    dashboard = NoiseDashboard()
    results = dashboard.analyze_all(raw_sensor_data)
    dashboard.display_summary(results)

    # Step 2: Symbolic pattern recognition
    symbolic_engine = SymbolicIntelligenceEngine()
    symbolic_signals = symbolic_engine.extract_resonant_patterns(results)
    alignment_report = symbolic_engine.calculate_cross_layer_alignment(symbolic_signals)

    print("\n🧠 SYMBOLIC INTELLIGENCE SUMMARY")
    print(f"Alignment Score: {alignment_report['alignment_score']}")
    print(f"Contributing Domains: {', '.join(alignment_report['contributing_domains'])}")
    print(f"System Coherence: {alignment_report['symbolic_consensus']}")
