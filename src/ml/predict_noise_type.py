"""
Noise Type Prediction Script
Classifies noise recordings using trained PyTorch model.
"""

import torch
import numpy as np
from feature_extraction import AudioFeatureExtractor
from noise_classifier_model import load_model
from database_schema import ANCDatabase
import os


class NoisePredictor:
    """Predict noise type for audio recordings."""

    def __init__(self, model_path='noise_classifier.pth', device='cpu'):
        """
        Initialize predictor.

        Args:
            model_path: Path to trained model
            device: Device to run inference on
        """
        self.device = device
        self.model, self.label_encoder, self.scaler = load_model(model_path, device)
        self.feature_extractor = AudioFeatureExtractor()

    def predict_from_audio(self, audio_data: np.ndarray) -> tuple:
        """
        Predict noise type from audio data.

        Args:
            audio_data: Audio waveform as numpy array

        Returns:
            (predicted_class, confidence, all_probabilities)
        """
        # Extract features
        features = self.feature_extractor.extract_feature_vector(audio_data)

        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # Convert to tensor
        features_tensor = torch.FloatTensor(features_scaled).to(self.device)

        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(features_tensor)
            probabilities = torch.softmax(outputs, dim=1)[0]
            confidence, predicted_idx = torch.max(probabilities, 0)

        # Get class name
        predicted_class = self.label_encoder.classes_[predicted_idx.item()]

        # Get all probabilities
        all_probs = {
            self.label_encoder.classes_[i]: probabilities[i].item()
            for i in range(len(self.label_encoder.classes_))
        }

        return predicted_class, confidence.item(), all_probs

    def predict_from_file(self, filepath: str) -> tuple:
        """
        Predict noise type from audio file.

        Args:
            filepath: Path to WAV file

        Returns:
            (predicted_class, confidence, all_probabilities)
        """
        import wave

        # Load WAV file
        with wave.open(filepath, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            audio_data = audio_data.astype(np.float64) / 32768.0

        return self.predict_from_audio(audio_data)

    def predict_from_database(self, db: ANCDatabase, recording_id: int) -> tuple:
        """
        Predict noise type for recording in database.

        Args:
            db: Database connection
            recording_id: Recording ID

        Returns:
            (predicted_class, confidence, all_probabilities)
        """
        # Get waveform from database
        db.cursor.execute("""
            SELECT waveform_id
            FROM audio_waveforms
            WHERE recording_id = ?
            LIMIT 1
        """, (recording_id,))

        result = db.cursor.fetchone()
        if not result:
            raise ValueError(f"No waveform found for recording {recording_id}")

        waveform_id = result[0]
        audio_data = db.get_waveform(waveform_id)

        return self.predict_from_audio(audio_data)

    def batch_predict_database(self, db_path='anc_system.db'):
        """
        Predict noise types for all recordings in database.

        Args:
            db_path: Path to database

        Returns:
            List of predictions
        """
        db = ANCDatabase(db_path)
        recordings = db.get_all_recordings()

        predictions = []

        print(f"Predicting noise types for {len(recordings)} recordings...")
        print("=" * 80)

        for rec in recordings:
            rec_id = rec[0]
            true_label = rec[5]  # environment_type

            try:
                predicted_class, confidence, all_probs = self.predict_from_database(db, rec_id)

                prediction = {
                    'recording_id': rec_id,
                    'true_label': true_label,
                    'predicted_label': predicted_class,
                    'confidence': confidence,
                    'probabilities': all_probs
                }

                predictions.append(prediction)

                # Print result
                match = "✓" if predicted_class == true_label else "✗"
                print(f"{match} Recording {rec_id}: True={true_label:<15} "
                      f"Predicted={predicted_class:<15} Confidence={confidence:.2%}")

            except Exception as e:
                print(f"✗ Recording {rec_id}: Error - {e}")

        db.close()

        # Calculate accuracy
        if predictions:
            correct = sum(1 for p in predictions if p['true_label'] == p['predicted_label'])
            accuracy = 100 * correct / len(predictions)
            print(f"\n{'─' * 80}")
            print(f"Overall Accuracy: {accuracy:.2f}% ({correct}/{len(predictions)})")

        return predictions


def predict_single_recording(recording_id, model_path='noise_classifier.pth', db_path='anc_system.db'):
    """
    Predict noise type for a single recording.

    Args:
        recording_id: Recording ID
        model_path: Path to trained model
        db_path: Path to database
    """
    print("=" * 80)
    print(f"PREDICTING NOISE TYPE FOR RECORDING {recording_id}")
    print("=" * 80)

    predictor = NoisePredictor(model_path)
    db = ANCDatabase(db_path)

    # Get recording info
    db.cursor.execute("""
        SELECT timestamp, environment_type, location, description, noise_level_db
        FROM noise_recordings
        WHERE recording_id = ?
    """, (recording_id,))

    rec_info = db.cursor.fetchone()
    if not rec_info:
        print(f"Error: Recording {recording_id} not found")
        db.close()
        return

    timestamp, env_type, location, description, noise_db = rec_info

    print(f"\nRecording Information:")
    print(f"  Timestamp: {timestamp}")
    print(f"  Location: {location}")
    print(f"  Description: {description}")
    print(f"  Noise Level: {noise_db:.2f} dB")
    print(f"  True Label: {env_type}")

    # Predict
    print(f"\n{'─' * 80}")
    print("Making prediction...")

    predicted_class, confidence, all_probs = predictor.predict_from_database(db, recording_id)

    print(f"\nPrediction Results:")
    print(f"  Predicted Class: {predicted_class}")
    print(f"  Confidence: {confidence:.2%}")

    print(f"\nAll Class Probabilities:")
    print(f"{'─' * 80}")
    sorted_probs = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)
    for class_name, prob in sorted_probs:
        bar = '█' * int(prob * 50)
        print(f"  {class_name:<15} {prob:>6.2%} {bar}")

    # Check correctness
    match = predicted_class == env_type
    print(f"\n{'─' * 80}")
    if match:
        print(f"✓ CORRECT PREDICTION!")
    else:
        print(f"✗ INCORRECT PREDICTION (Expected: {env_type})")

    db.close()


def main():
    """Main prediction demo."""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'batch':
            # Batch prediction
            predictor = NoisePredictor()
            predictions = predictor.batch_predict_database()

            # Save predictions
            import json
            with open('predictions.json', 'w') as f:
                json.dump(predictions, f, indent=2, default=str)
            print(f"\n✓ Predictions saved to predictions.json")

        elif sys.argv[1].isdigit():
            # Single recording prediction
            recording_id = int(sys.argv[1])
            predict_single_recording(recording_id)

        else:
            print("Usage:")
            print("  python predict_noise_type.py <recording_id>  - Predict single recording")
            print("  python predict_noise_type.py batch           - Predict all recordings")
    else:
        # Demo: predict latest recording
        db = ANCDatabase('anc_system.db')
        recordings = db.get_all_recordings()
        db.close()

        if recordings:
            latest_id = recordings[0][0]
            predict_single_recording(latest_id)
        else:
            print("No recordings found in database")


if __name__ == "__main__":
    main()
