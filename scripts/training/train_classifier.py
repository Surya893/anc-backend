"""
Training Script for Noise Classification Model
Trains PyTorch model on extracted audio features with evaluation metrics.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
from tqdm import tqdm
import time
from datetime import datetime

from noise_classifier_model import (
    NoiseClassifierMLP,
    NoiseClassifierCNN,
    NoiseClassifierEnsemble,
    create_data_loaders,
    save_model
)
from database_schema import ANCDatabase


class NoiseClassifierTrainer:
    """Trainer class for noise classification models."""

    def __init__(self, model, device='cpu', learning_rate=0.001, weight_decay=1e-5):
        """
        Initialize trainer.

        Args:
            model: PyTorch model
            device: Device to train on ('cpu' or 'cuda')
            learning_rate: Learning rate
            weight_decay: L2 regularization weight
        """
        self.model = model.to(device)
        self.device = device

        # Loss function
        self.criterion = nn.CrossEntropyLoss()

        # Optimizer
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )

        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )

        # Training history
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': [],
            'learning_rates': []
        }

    def train_epoch(self, train_loader):
        """
        Train for one epoch.

        Args:
            train_loader: Training data loader

        Returns:
            Average loss and accuracy
        """
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc='Training')
        for features, labels in pbar:
            features, labels = features.to(self.device), labels.to(self.device)

            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(features)
            loss = self.criterion(outputs, labels)

            # Backward pass
            loss.backward()
            self.optimizer.step()

            # Statistics
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            # Update progress bar
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100 * correct / total:.2f}%'
            })

        avg_loss = total_loss / len(train_loader)
        accuracy = 100 * correct / total

        return avg_loss, accuracy

    def validate(self, val_loader):
        """
        Validate model.

        Args:
            val_loader: Validation data loader

        Returns:
            Average loss and accuracy
        """
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0

        all_labels = []
        all_predictions = []

        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(self.device), labels.to(self.device)

                # Forward pass
                outputs = self.model(features)
                loss = self.criterion(outputs, labels)

                # Statistics
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

                all_labels.extend(labels.cpu().numpy())
                all_predictions.extend(predicted.cpu().numpy())

        avg_loss = total_loss / len(val_loader)
        accuracy = 100 * correct / total

        return avg_loss, accuracy, all_labels, all_predictions

    def train(self, train_loader, val_loader, epochs=50, early_stopping_patience=10):
        """
        Train model with validation and early stopping.

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Number of epochs
            early_stopping_patience: Patience for early stopping

        Returns:
            Training history
        """
        print("=" * 80)
        print("TRAINING NOISE CLASSIFIER")
        print("=" * 80)
        print(f"Device: {self.device}")
        print(f"Model: {self.model.__class__.__name__}")
        print(f"Epochs: {epochs}")
        print(f"Early stopping patience: {early_stopping_patience}")
        print("=" * 80)

        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None

        start_time = time.time()

        for epoch in range(epochs):
            print(f"\nEpoch {epoch+1}/{epochs}")
            print("─" * 80)

            # Train
            train_loss, train_acc = self.train_epoch(train_loader)

            # Validate
            val_loss, val_acc, _, _ = self.validate(val_loader)

            # Update learning rate
            self.scheduler.step(val_loss)

            # Record history
            current_lr = self.optimizer.param_groups[0]['lr']
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            self.history['learning_rates'].append(current_lr)

            # Print epoch summary
            print(f"\nEpoch {epoch+1} Summary:")
            print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
            print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.2f}%")
            print(f"  Learning Rate: {current_lr:.6f}")

            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_model_state = self.model.state_dict().copy()
                print(f"  ✓ New best model (val_loss: {val_loss:.4f})")
            else:
                patience_counter += 1
                print(f"  No improvement ({patience_counter}/{early_stopping_patience})")

            if patience_counter >= early_stopping_patience:
                print(f"\nEarly stopping triggered after {epoch+1} epochs")
                break

        # Restore best model
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            print(f"\n✓ Restored best model (val_loss: {best_val_loss:.4f})")

        training_time = time.time() - start_time
        print(f"\nTraining completed in {training_time:.2f} seconds")

        return self.history

    def evaluate_detailed(self, test_loader, label_encoder):
        """
        Detailed evaluation with metrics.

        Args:
            test_loader: Test data loader
            label_encoder: Label encoder for class names

        Returns:
            Dictionary of metrics
        """
        print("\n" + "=" * 80)
        print("DETAILED EVALUATION")
        print("=" * 80)

        # Get predictions
        _, accuracy, all_labels, all_predictions = self.validate(test_loader)

        # Compute metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            all_labels, all_predictions, average=None
        )

        # Overall metrics
        overall_precision, overall_recall, overall_f1, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average='weighted'
        )

        # Confusion matrix
        cm = confusion_matrix(all_labels, all_predictions)

        # Print results
        class_names = label_encoder.classes_
        print(f"\nOverall Accuracy: {accuracy:.2f}%")
        print(f"Weighted Precision: {overall_precision:.4f}")
        print(f"Weighted Recall: {overall_recall:.4f}")
        print(f"Weighted F1-Score: {overall_f1:.4f}")

        print("\nPer-Class Metrics:")
        print("─" * 80)
        print(f"{'Class':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
        print("─" * 80)
        for i, class_name in enumerate(class_names):
            print(f"{class_name:<15} {precision[i]:<12.4f} {recall[i]:<12.4f} "
                  f"{f1[i]:<12.4f} {support[i]:<10}")

        print("\nConfusion Matrix:")
        print("─" * 80)
        print("Predicted →")
        print(f"{'Actual ↓':<15}", end='')
        for class_name in class_names:
            print(f"{class_name[:10]:<12}", end='')
        print()
        print("─" * 80)
        for i, class_name in enumerate(class_names):
            print(f"{class_name:<15}", end='')
            for j in range(len(class_names)):
                print(f"{cm[i][j]:<12}", end='')
            print()

        metrics = {
            'accuracy': accuracy,
            'precision': overall_precision,
            'recall': overall_recall,
            'f1': overall_f1,
            'per_class_precision': precision,
            'per_class_recall': recall,
            'per_class_f1': f1,
            'support': support,
            'confusion_matrix': cm,
            'class_names': class_names
        }

        return metrics

    def plot_training_history(self, save_path='training_history.png'):
        """
        Plot training history.

        Args:
            save_path: Path to save plot
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        epochs = range(1, len(self.history['train_loss']) + 1)

        # Loss plot
        axes[0, 0].plot(epochs, self.history['train_loss'], 'b-', label='Train Loss')
        axes[0, 0].plot(epochs, self.history['val_loss'], 'r-', label='Val Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training and Validation Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Accuracy plot
        axes[0, 1].plot(epochs, self.history['train_acc'], 'b-', label='Train Acc')
        axes[0, 1].plot(epochs, self.history['val_acc'], 'r-', label='Val Acc')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy (%)')
        axes[0, 1].set_title('Training and Validation Accuracy')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # Learning rate plot
        axes[1, 0].plot(epochs, self.history['learning_rates'], 'g-')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Learning Rate')
        axes[1, 0].set_title('Learning Rate Schedule')
        axes[1, 0].set_yscale('log')
        axes[1, 0].grid(True, alpha=0.3)

        # Loss difference plot
        loss_diff = [abs(t - v) for t, v in zip(self.history['train_loss'], self.history['val_loss'])]
        axes[1, 1].plot(epochs, loss_diff, 'm-')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('|Train Loss - Val Loss|')
        axes[1, 1].set_title('Train-Validation Loss Difference')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Training history plot saved to {save_path}")


def main():
    """Main training function."""
    print("=" * 80)
    print("NOISE CLASSIFICATION MODEL TRAINING")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check for GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")

    # Create data loaders
    print("\nLoading data...")
    train_loader, test_loader, train_dataset, test_dataset = create_data_loaders(
        features_file='features.npz',
        batch_size=32,
        test_size=0.2,
        random_state=42
    )

    input_dim = train_dataset.get_feature_dim()
    num_classes = train_dataset.get_num_classes()

    print(f"\nModel configuration:")
    print(f"  Input dimension: {input_dim}")
    print(f"  Number of classes: {num_classes}")
    print(f"  Classes: {train_dataset.label_encoder.classes_}")

    # Create model
    model = NoiseClassifierMLP(
        input_dim=input_dim,
        num_classes=num_classes,
        hidden_dims=[256, 128, 64],
        dropout=0.3
    )

    print(f"\nModel parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Create trainer
    trainer = NoiseClassifierTrainer(
        model=model,
        device=device,
        learning_rate=0.001,
        weight_decay=1e-5
    )

    # Train model
    history = trainer.train(
        train_loader=train_loader,
        val_loader=test_loader,
        epochs=100,
        early_stopping_patience=15
    )

    # Evaluate
    metrics = trainer.evaluate_detailed(test_loader, train_dataset.label_encoder)

    # Plot training history
    trainer.plot_training_history('training_history.png')

    # Save model
    save_model(
        model=model,
        label_encoder=train_dataset.label_encoder,
        scaler=train_dataset.scaler,
        filepath='noise_classifier.pth'
    )

    # Save metrics
    np.savez(
        'training_metrics.npz',
        history=history,
        metrics=metrics
    )

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE!")
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nFinal Test Accuracy: {metrics['accuracy']:.2f}%")
    print(f"Final F1-Score: {metrics['f1']:.4f}")


if __name__ == "__main__":
    main()
