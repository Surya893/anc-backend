"""
Integration example: Active Noise Cancellation with Database Storage
Combines the OpenAirNoiseCancellation algorithm with SQLite persistence.
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import time
from database_schema import ANCDatabase


class OpenAirNoiseCancellationDB:
    """
    Enhanced OpenAirNoiseCancellation with database persistence.
    Stores all recordings, waveforms, and model artifacts in SQLite.
    """

    def __init__(self, sampling_rate=44100, filter_length=1024, db_path="anc_system.db"):
        self.sampling_rate = sampling_rate
        self.filter_length = filter_length
        self.reference_noise = np.zeros(self.filter_length)
        self.coefficients = np.zeros(self.filter_length)
        self.mu = 0.01  # Adaptation rate

        # Database connection
        self.db = ANCDatabase(db_path)
        self.model_id = None
        self.recording_id = None
        self.session_id = None

        # Initialize model version in database
        self._initialize_model()

    def _initialize_model(self):
        """Register this model instance in the database."""
        version_name = f"LMS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.model_id = self.db.insert_model_version(
            version_name=version_name,
            version_number="1.0.0",
            filter_length=self.filter_length,
            adaptation_rate=self.mu,
            algorithm_type="LMS",
            description="Adaptive LMS filter for noise cancellation",
            is_active=True
        )
        print(f"Model initialized with ID: {self.model_id}")

    def start_recording(self, duration_seconds, environment_type=None,
                       location=None, description=None):
        """Start a new recording session."""
        num_samples = int(duration_seconds * self.sampling_rate)
        self.recording_id = self.db.insert_noise_recording(
            duration_seconds=duration_seconds,
            sampling_rate=self.sampling_rate,
            num_samples=num_samples,
            environment_type=environment_type,
            location=location,
            description=description
        )
        print(f"Recording started with ID: {self.recording_id}")
        return self.recording_id

    def update_reference_noise(self, ambient_noise, save_to_db=True):
        """Update reference noise with ambient noise and optionally save to database."""
        self.reference_noise = ambient_noise[:self.filter_length]

        if save_to_db and self.recording_id:
            # Store reference noise waveform
            self.db.insert_waveform(
                recording_id=self.recording_id,
                waveform_type="reference_noise",
                waveform_array=self.reference_noise
            )

    def cancel_noise(self, input_signal, save_to_db=True, iteration=None):
        """
        Apply adaptive filtering and optionally save results to database.
        """
        start_time = time.time()

        # Apply adaptive filtering
        output_signal = np.convolve(input_signal, self.coefficients, mode='same')

        # Ensure that 'error' has the correct size
        output_signal = output_signal[:len(self.reference_noise)]
        error = self.reference_noise - output_signal
        self.coefficients += self.mu * np.convolve(input_signal, error, mode='full')[:self.filter_length]

        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        if save_to_db and self.recording_id:
            # Store the noise-cancelled signal
            self.db.insert_waveform(
                recording_id=self.recording_id,
                waveform_type="noise_cancelled",
                waveform_array=output_signal
            )

            # Store error signal
            self.db.insert_waveform(
                recording_id=self.recording_id,
                waveform_type="error_signal",
                waveform_array=error
            )

            # Store updated coefficients
            self.db.insert_model_coefficients(
                model_id=self.model_id,
                coefficients=self.coefficients,
                recording_id=self.recording_id,
                iteration_number=iteration
            )

            # Store training history
            if iteration is not None:
                mse = np.mean(error ** 2)
                self.db.insert_training_history(
                    model_id=self.model_id,
                    iteration_number=iteration,
                    error_value=float(mse),
                    learning_rate=self.mu,
                    coefficient_snapshot=self.coefficients
                )

        return output_signal, processing_time

    def start_processing_session(self, recording_id=None, configuration=None):
        """Start a processing session for tracking."""
        if recording_id:
            self.recording_id = recording_id

        self.session_id = self.db.insert_processing_session(
            model_id=self.model_id,
            recording_id=self.recording_id,
            configuration=configuration
        )
        print(f"Processing session started with ID: {self.session_id}")
        return self.session_id

    def end_processing_session(self, final_error=None, convergence_achieved=None,
                              processing_duration_ms=None):
        """End the current processing session and store metrics."""
        if self.session_id:
            self.db.update_processing_session(
                session_id=self.session_id,
                processing_duration_ms=processing_duration_ms,
                final_error=final_error,
                convergence_achieved=convergence_achieved
            )

    def save_performance_metrics(self, snr_improvement=None, noise_reduction_db=None,
                                processing_latency=None):
        """Save performance metrics for the current session."""
        if not self.session_id:
            print("Warning: No active session to save metrics")
            return

        if snr_improvement is not None:
            self.db.insert_performance_metric(
                session_id=self.session_id,
                metric_type="snr_improvement",
                metric_value=snr_improvement,
                metric_unit="dB"
            )

        if noise_reduction_db is not None:
            self.db.insert_performance_metric(
                session_id=self.session_id,
                metric_type="noise_reduction_db",
                metric_value=noise_reduction_db,
                metric_unit="dB"
            )

        if processing_latency is not None:
            self.db.insert_performance_metric(
                session_id=self.session_id,
                metric_type="processing_latency",
                metric_value=processing_latency,
                metric_unit="ms"
            )

    def close(self):
        """Close database connection."""
        self.db.close()


def run_anc_with_persistence():
    """
    Example: Run noise cancellation with full database persistence.
    """
    print("=" * 60)
    print("ANC System with Database Persistence - Example")
    print("=" * 60)

    # Initialize ANC system with database
    anc = OpenAirNoiseCancellationDB(
        sampling_rate=44100,
        filter_length=1024,
        db_path="anc_system.db"
    )

    # Generate example data
    print("\n1. Generating test signals...")
    time_vector = np.linspace(0, 1, 1000)
    clean_signal = np.sin(2 * np.pi * 5 * time_vector)  # 5 Hz sine wave
    ambient_noise = 0.5 * np.random.randn(1000)  # Random noise
    noisy_signal = clean_signal + ambient_noise

    # Start recording
    print("\n2. Starting recording session...")
    anc.start_recording(
        duration_seconds=1.0,
        environment_type="laboratory",
        location="Test Lab",
        description="Example noise cancellation test"
    )

    # Store the original signals
    print("\n3. Storing original signals...")
    anc.db.insert_waveform(
        recording_id=anc.recording_id,
        waveform_type="clean_signal",
        waveform_array=clean_signal
    )
    anc.db.insert_waveform(
        recording_id=anc.recording_id,
        waveform_type="ambient_noise",
        waveform_array=ambient_noise
    )

    # Update reference noise
    print("\n4. Updating reference noise...")
    anc.update_reference_noise(ambient_noise, save_to_db=True)

    # Start processing session
    print("\n5. Starting processing session...")
    anc.start_processing_session(
        configuration={
            "algorithm": "LMS",
            "adaptation_rate": 0.01,
            "filter_length": 1024
        }
    )

    # Perform noise cancellation
    print("\n6. Performing noise cancellation...")
    total_time = 0
    for iteration in range(1, 6):
        noise_cancelled_signal, proc_time = anc.cancel_noise(
            clean_signal,
            save_to_db=(iteration == 5),  # Save only last iteration
            iteration=iteration
        )
        total_time += proc_time
        print(f"   Iteration {iteration}: Processing time = {proc_time:.2f} ms")

    # Calculate performance metrics
    print("\n7. Calculating performance metrics...")
    snr_before = 10 * np.log10(np.mean(clean_signal ** 2) / np.mean(ambient_noise ** 2))
    error = clean_signal[:len(noise_cancelled_signal)] - noise_cancelled_signal
    snr_after = 10 * np.log10(np.mean(clean_signal[:len(noise_cancelled_signal)] ** 2) / np.mean(error ** 2))
    snr_improvement = snr_after - snr_before

    print(f"   SNR before: {snr_before:.2f} dB")
    print(f"   SNR after: {snr_after:.2f} dB")
    print(f"   SNR improvement: {snr_improvement:.2f} dB")

    # Save metrics
    final_mse = np.mean(error ** 2)
    anc.save_performance_metrics(
        snr_improvement=snr_improvement,
        noise_reduction_db=abs(snr_improvement),
        processing_latency=total_time / 5  # Average latency
    )

    # End processing session
    print("\n8. Ending processing session...")
    anc.end_processing_session(
        final_error=float(final_mse),
        convergence_achieved=(final_mse < 0.1),
        processing_duration_ms=total_time
    )

    # Retrieve and display statistics
    print("\n9. Database Statistics:")
    recordings = anc.db.get_all_recordings()
    print(f"   Total recordings: {len(recordings)}")

    active_model = anc.db.get_active_model()
    if active_model:
        print(f"   Active model: {active_model[1]} (v{active_model[2]})")
        print(f"   Filter length: {active_model[3]}")
        print(f"   Adaptation rate: {active_model[4]}")

    metrics = anc.db.get_session_metrics(anc.session_id)
    print(f"   Session metrics recorded: {len(metrics)}")
    for metric in metrics:
        print(f"     - {metric[0]}: {metric[1]:.4f} {metric[2]}")

    # Visualization
    print("\n10. Creating visualization...")
    plt.figure(figsize=(12, 10))

    plt.subplot(4, 1, 1)
    plt.plot(time_vector, clean_signal, label='Original Clean Signal', color='blue')
    plt.legend()
    plt.ylabel('Amplitude')
    plt.title('ANC System - Signal Processing Pipeline')

    plt.subplot(4, 1, 2)
    plt.plot(time_vector, ambient_noise, label='Ambient Noise', color='red')
    plt.legend()
    plt.ylabel('Amplitude')

    plt.subplot(4, 1, 3)
    plt.plot(time_vector[:len(noise_cancelled_signal)], clean_signal[:len(noise_cancelled_signal)],
             label='Original Clean Signal', color='blue', alpha=0.7)
    plt.plot(time_vector[:len(noise_cancelled_signal)], noise_cancelled_signal,
             label='Noise-Cancelled Signal', color='green', linestyle='--')
    plt.legend()
    plt.ylabel('Amplitude')

    plt.subplot(4, 1, 4)
    plt.plot(time_vector[:len(error)], error, label='Error Signal', color='orange')
    plt.legend()
    plt.ylabel('Amplitude')
    plt.xlabel('Time (s)')

    plt.tight_layout()
    plt.savefig('anc_results.png', dpi=150)
    print("   Visualization saved to: anc_results.png")

    # Close database connection
    anc.close()

    print("\n" + "=" * 60)
    print("✓ ANC processing completed successfully!")
    print("✓ All data stored in database: anc_system.db")
    print("=" * 60)


if __name__ == "__main__":
    run_anc_with_persistence()
