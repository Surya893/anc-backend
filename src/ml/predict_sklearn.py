"""
Noise Type Prediction Script (scikit-learn version)
Predict noise types from database recordings using sklearn model.
"""

import numpy as np
import pickle
import sys
from database_schema import ANCDatabase
from feature_extraction import AudioFeatureExtractor


class NoisePredictor:
    """Predict noise types using trained sklearn model."""

    def __init__(self, model_path='noise_classifier_sklearn.pkl'):
        """
        Initialize predictor.

        Args:
            model_path: Path to trained model file
        """
        print(f"Loading model from {model_path}...")

        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.class_names = list(self.label_encoder.classes_)

        print(f"✓ Model loaded successfully")
        print(f"  Classes: {self.class_names}")

    def predict_from_recording(self, recording_id, db_path='anc_system.db'):
        """
        Predict noise type from database recording.

        Args:
            recording_id: Recording ID in database
            db_path: Path to database

        Returns:
            (predicted_class, confidence, probabilities)
        """
        # Load recording from database
        db = ANCDatabase(db_path)

        # Get specific recording
        all_recordings = db.get_all_recordings()
        recording = None
        for rec in all_recordings:
            if rec[0] == recording_id:
                recording = rec
                break

        if not recording:
            db.close()
            raise ValueError(f"Recording {recording_id} not found")

        # Get waveform ID from audio_waveforms table
        db.cursor.execute("""
            SELECT waveform_id
            FROM audio_waveforms
            WHERE recording_id = ?
            LIMIT 1
        """, (recording_id,))

        result = db.cursor.fetchone()
        if not result:
            db.close()
            raise ValueError(f"No waveform found for recording {recording_id}")

        waveform_id = result[0]
        original_waveform = db.get_waveform(waveform_id)

        db.close()

        if original_waveform is None:
            raise ValueError(f"Failed to load waveform {waveform_id}")

        # Extract features
        return self.predict_from_audio(original_waveform, recording)

    def predict_from_audio(self, audio_data, recording_info=None):
        """
        Predict noise type from audio data.

        Args:
            audio_data: Audio waveform (numpy array)
            recording_info: Optional recording metadata

        Returns:
            (predicted_class, confidence, probabilities)
        """
        # Extract features
        extractor = AudioFeatureExtractor()
        features = extractor.extract_feature_vector(audio_data)

        # Reshape for prediction
        features = features.reshape(1, -1)

        # Normalize
        features_scaled = self.scaler.transform(features)

        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        # Get class name
        predicted_class = self.label_encoder.inverse_transform([prediction])[0]
        confidence = probabilities[prediction]

        # Create probability dictionary
        prob_dict = {}
        for i, class_name in enumerate(self.class_names):
            class_idx = self.label_encoder.transform([class_name])[0]
            prob_dict[class_name] = probabilities[class_idx]

        return predicted_class, confidence, prob_dict


def predict_single(recording_id):
    """Predict single recording and display results."""
    print("=" * 80)
    print(f"PREDICTING NOISE TYPE FOR RECORDING {recording_id}")
    print("=" * 80)

    # Load predictor
    predictor = NoisePredictor()

    # Get recording info
    db = ANCDatabase('anc_system.db')

    # Find specific recording
    all_recordings = db.get_all_recordings()
    recording = None
    for rec in all_recordings:
        if rec[0] == recording_id:
            recording = rec
            break

    if not recording:
        print(f"Error: Recording {recording_id} not found")
        db.close()
        return

    # Unpack recording fields: recording_id, timestamp, duration_seconds, sampling_rate,
    # num_samples, environment_type, noise_level_db, location
    rec_id, timestamp, duration, sample_rate, num_samples, env_type, noise_db, location = recording

    print(f"\nRecording Information:")
    print(f"  Timestamp: {timestamp}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Location: {location}")
    print(f"  True Label: {env_type}")

    db.close()

    # Predict
    print(f"\nExtracting features and predicting...")
    predicted_class, confidence, probabilities = predictor.predict_from_recording(recording_id)

    print(f"\nPrediction Results:")
    print(f"  Predicted Class: {predicted_class}")
    print(f"  Confidence: {confidence*100:.2f}%")

    # Display all class probabilities
    print(f"\nAll Class Probabilities:")
    print("─" * 80)

    # Sort by probability
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)

    for class_name, prob in sorted_probs:
        bar_length = int(prob * 50)
        bar = '█' * bar_length
        print(f"  {class_name:<15} {prob*100:>6.2f}% {bar}")

    print("─" * 80)

    # Check if correct
    if env_type and predicted_class == env_type:
        print("✓ CORRECT PREDICTION!")
    elif env_type:
        print(f"✗ INCORRECT - Expected: {env_type}")

    return predicted_class, confidence


def predict_batch():
    """Predict all recordings and show statistics."""
    print("=" * 80)
    print("BATCH PREDICTION - ALL RECORDINGS")
    print("=" * 80)

    # Load predictor
    predictor = NoisePredictor()

    # Get all recordings
    db = ANCDatabase('anc_system.db')
    recordings = db.get_all_recordings()
    db.close()

    print(f"\nPredicting noise types for {len(recordings)} recordings...\n")

    results = []
    correct = 0
    total = 0

    for recording in recordings:
        # Unpack: recording_id, timestamp, duration_seconds, sampling_rate,
        # num_samples, environment_type, noise_level_db, location
        rec_id, timestamp, duration, sample_rate, num_samples, env_type, noise_db, location = recording

        try:
            predicted, confidence, probs = predictor.predict_from_recording(rec_id)

            is_correct = (predicted == env_type)
            if is_correct:
                correct += 1
            total += 1

            status = "✓" if is_correct else "✗"

            print(f"{status} Recording {rec_id:>2}: True={env_type:<12} "
                  f"Predicted={predicted:<12} Confidence={confidence*100:>6.2f}%")

            results.append({
                'id': rec_id,
                'true': env_type,
                'predicted': predicted,
                'confidence': confidence,
                'correct': is_correct
            })

        except Exception as e:
            print(f"✗ Recording {rec_id}: Error - {e}")

    print("─" * 80)
    accuracy = (correct / total * 100) if total > 0 else 0
    print(f"Overall Accuracy: {accuracy:.2f}% ({correct}/{total})")

    # Calculate average confidence
    avg_confidence = np.mean([r['confidence'] for r in results]) * 100
    print(f"Average Confidence: {avg_confidence:.2f}%")

    return results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python predict_sklearn.py <recording_id>  - Predict single recording")
        print("  python predict_sklearn.py batch           - Predict all recordings")
        sys.exit(1)

    if sys.argv[1].lower() == 'batch':
        predict_batch()
    else:
        try:
            recording_id = int(sys.argv[1])
            predict_single(recording_id)
        except ValueError as e:
            print(f"Error: Invalid recording ID: {sys.argv[1]}")
            print(f"Details: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error during prediction: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
