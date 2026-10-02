# dashboard/dashboard.py

from software.quantum.quantum_processor import QuantumNoiseProcessor
from software.biological.biological_processor import BiologicalNoiseProcessor
from software.electromagnetic.em_processor import EMFieldNoiseProcessor
from software.planetary.gaia_processor import GaiaSystemNoiseProcessor

class NoiseDashboard:
    def __init__(self):
        self.quantum = QuantumNoiseProcessor()
        self.biological = BiologicalNoiseProcessor()
        self.electromagnetic = EMFieldNoiseProcessor()
        self.gaia = GaiaSystemNoiseProcessor()

    DISPLAY_LABELS = {
        'quantum': '🌌 QUANTUM NOISE ANALYSIS',
        'biological': '🌱 BIOLOGICAL NETWORK CHATTER',
        'electromagnetic': '⚡ ELECTROMAGNETIC FIELD EFFECTS',
        'planetary': '🌍 GAIA SYSTEM INTELLIGENCE',
    }

    def analyze_all(self, raw_sensor_data):
        q_result = self.quantum.analyze_quantum_noise(raw_sensor_data['molecular'])
        b_result = self.biological.analyze_biological_noise(raw_sensor_data['chemical'])
        e_result = self.electromagnetic.analyze_em_field_noise(raw_sensor_data['motion'])
        g_result = self.gaia.analyze_gaia_noise(raw_sensor_data['atmospheric'])

        return {
            'quantum': q_result,
            'biological': b_result,
            'electromagnetic': e_result,
            'planetary': g_result,
        }

    def display_summary(self, analysis_result):
        for domain, results in analysis_result.items():
            label = self.DISPLAY_LABELS.get(domain, domain)
            print(f"\n{label}")
            for key, value in results.items():
                print(f"  {key.replace('_', ' ').capitalize()}: {value}")
