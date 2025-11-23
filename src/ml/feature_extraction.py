"""
Audio Feature Extraction Module
Extracts MFCC and other audio features from stored noise recordings.
"""

import numpy as np
import librosa
from typing import Dict, Tuple, Optional
from database_schema import ANCDatabase


class AudioFeatureExtractor:
    """
    Extract audio features for noise classification.
    Supports MFCC, spectral features, and temporal features.
    """

    def __init__(self, sample_rate=44100, n_mfcc=13, n_fft=2048, hop_length=512):
        """
        Initialize feature extractor.

        Args:
            sample_rate: Audio sample rate (Hz)
            n_mfcc: Number of MFCC coefficients
            n_fft: FFT window size
            hop_length: Number of samples between successive frames
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length

    def extract_mfcc(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features from audio data.

        Args:
            audio_data: Audio waveform as numpy array

        Returns:
            MFCC features (n_mfcc x time_frames)
        """
        mfccs = librosa.feature.mfcc(
            y=audio_data,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )
        return mfccs

    def extract_mfcc_delta(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract MFCC and delta (first derivative) features.

        Args:
            audio_data: Audio waveform

        Returns:
            Tuple of (mfcc, delta_mfcc)
        """
        mfccs = self.extract_mfcc(audio_data)

        # Adjust width for short sequences
        width = min(9, mfccs.shape[1])
        if width < 3:
            # Too short for delta, return zeros
            delta_mfccs = np.zeros_like(mfccs)
        else:
            delta_mfccs = librosa.feature.delta(mfccs, width=width)

        return mfccs, delta_mfccs

    def extract_spectral_features(self, audio_data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extract spectral features from audio.

        Args:
            audio_data: Audio waveform

        Returns:
            Dictionary of spectral features
        """
        features = {}

        # Spectral centroid
        features['spectral_centroid'] = librosa.feature.spectral_centroid(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )[0]

        # Spectral rolloff
        features['spectral_rolloff'] = librosa.feature.spectral_rolloff(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )[0]

        # Zero crossing rate
        features['zero_crossing_rate'] = librosa.feature.zero_crossing_rate(
            y=audio_data,
            frame_length=self.n_fft,
            hop_length=self.hop_length
        )[0]

        # RMS energy
        features['rms'] = librosa.feature.rms(
            y=audio_data,
            frame_length=self.n_fft,
            hop_length=self.hop_length
        )[0]

        return features

    def extract_chroma_features(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract chroma features (pitch class profiles).

        Args:
            audio_data: Audio waveform

        Returns:
            Chroma features (12 x time_frames)
        """
        chroma = librosa.feature.chroma_stft(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length
        )
        return chroma

    def extract_all_features(self, audio_data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extract comprehensive feature set for classification.

        Args:
            audio_data: Audio waveform

        Returns:
            Dictionary containing all features
        """
        features = {}

        # MFCC and deltas
        mfccs, delta_mfccs = self.extract_mfcc_delta(audio_data)
        features['mfcc'] = mfccs
        features['delta_mfcc'] = delta_mfccs

        # Spectral features
        spectral_features = self.extract_spectral_features(audio_data)
        features.update(spectral_features)

        # Chroma features
        features['chroma'] = self.extract_chroma_features(audio_data)

        return features

    def compute_feature_statistics(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Compute statistical summaries of features for fixed-length representation.

        Args:
            features: Dictionary of time-varying features

        Returns:
            Fixed-length feature vector
        """
        feature_stats = []

        for name, feat in features.items():
            if feat.ndim == 1:
                feat = feat.reshape(1, -1)

            # Compute statistics along time axis
            mean = np.mean(feat, axis=1)
            std = np.std(feat, axis=1)
            min_val = np.min(feat, axis=1)
            max_val = np.max(feat, axis=1)

            # Concatenate statistics
            feature_stats.extend([mean, std, min_val, max_val])

        # Flatten to 1D vector
        feature_vector = np.concatenate([f.flatten() for f in feature_stats])

        return feature_vector

    def extract_feature_vector(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract complete fixed-length feature vector for classification.

        Args:
            audio_data: Audio waveform

        Returns:
            Fixed-length feature vector
        """
        # Extract all features
        features = self.extract_all_features(audio_data)

        # Compute statistics for fixed-length representation
        feature_vector = self.compute_feature_statistics(features)

        return feature_vector

    def extract_from_database(self, db: ANCDatabase, recording_id: int) -> Optional[np.ndarray]:
        """
        Extract features directly from database recording.

        Args:
            db: Database connection
            recording_id: Recording ID

        Returns:
            Feature vector or None if not found
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
            return None

        waveform_id = result[0]
        audio_data = db.get_waveform(waveform_id)

        if audio_data is None:
            return None

        # Extract features
        feature_vector = self.extract_feature_vector(audio_data)

        return feature_vector


def batch_extract_features(db_path="anc_system.db", output_file="features.npz"):
    """
    Extract features from all recordings in database and save to file.

    Args:
        db_path: Path to database
        output_file: Output file for features

    Returns:
        Dictionary with features, labels, and metadata
    """
    db = ANCDatabase(db_path)
    extractor = AudioFeatureExtractor()

    # Get all recordings
    recordings = db.get_all_recordings()

    features_list = []
    labels_list = []
    recording_ids = []

    print(f"Extracting features from {len(recordings)} recordings...")

    for rec in recordings:
        rec_id = rec[0]
        environment = rec[5]  # environment_type

        if environment is None:
            continue

        # Extract features
        feature_vector = extractor.extract_from_database(db, rec_id)

        if feature_vector is not None:
            features_list.append(feature_vector)
            labels_list.append(environment)
            recording_ids.append(rec_id)
            print(f"  ✓ Recording {rec_id}: {environment} ({len(feature_vector)} features)")

    db.close()

    # Convert to numpy arrays
    features = np.array(features_list)
    labels = np.array(labels_list)
    recording_ids = np.array(recording_ids)

    # Save to file
    np.savez(
        output_file,
        features=features,
        labels=labels,
        recording_ids=recording_ids
    )

    print(f"\n✓ Features saved to {output_file}")
    print(f"  Shape: {features.shape}")
    print(f"  Classes: {np.unique(labels)}")

    return {
        'features': features,
        'labels': labels,
        'recording_ids': recording_ids
    }


if __name__ == "__main__":
    # Demo: Extract features from database
    print("=" * 80)
    print("AUDIO FEATURE EXTRACTION")
    print("=" * 80)

    # Extract features from all recordings
    data = batch_extract_features()

    print(f"\nFeature extraction complete!")
    print(f"Total samples: {len(data['features'])}")
    print(f"Feature dimension: {data['features'].shape[1]}")
    print(f"Unique labels: {np.unique(data['labels'])}")
