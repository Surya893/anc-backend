"""
PyTorch Neural Network Model for Noise Classification
Classifies different noise types (traffic, alarms, office, etc.) using MFCC features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import pickle


class NoiseDataset(Dataset):
    """PyTorch Dataset for noise classification."""

    def __init__(self, features, labels, label_encoder=None, scaler=None, fit_transform=False):
        """
        Initialize dataset.

        Args:
            features: Feature vectors (N x D)
            labels: String labels (N,)
            label_encoder: LabelEncoder for labels
            scaler: StandardScaler for features
            fit_transform: If True, fit encoder/scaler; else just transform
        """
        self.features = features
        self.labels = labels

        # Encode labels
        if label_encoder is None:
            self.label_encoder = LabelEncoder()
            self.encoded_labels = self.label_encoder.fit_transform(labels)
        else:
            self.label_encoder = label_encoder
            if fit_transform:
                self.encoded_labels = self.label_encoder.fit_transform(labels)
            else:
                self.encoded_labels = self.label_encoder.transform(labels)

        # Scale features
        if scaler is None:
            self.scaler = StandardScaler()
            self.scaled_features = self.scaler.fit_transform(features)
        else:
            self.scaler = scaler
            if fit_transform:
                self.scaled_features = self.scaler.fit_transform(features)
            else:
                self.scaled_features = self.scaler.transform(features)

        # Convert to tensors
        self.features_tensor = torch.FloatTensor(self.scaled_features)
        self.labels_tensor = torch.LongTensor(self.encoded_labels)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features_tensor[idx], self.labels_tensor[idx]

    def get_num_classes(self):
        return len(self.label_encoder.classes_)

    def get_feature_dim(self):
        return self.features.shape[1]


class NoiseClassifierMLP(nn.Module):
    """Multi-Layer Perceptron for noise classification."""

    def __init__(self, input_dim, num_classes, hidden_dims=[256, 128, 64], dropout=0.3):
        """
        Initialize MLP classifier.

        Args:
            input_dim: Input feature dimension
            num_classes: Number of output classes
            hidden_dims: List of hidden layer dimensions
            dropout: Dropout probability
        """
        super(NoiseClassifierMLP, self).__init__()

        self.input_dim = input_dim
        self.num_classes = num_classes

        # Build layers
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim

        # Output layer
        layers.append(nn.Linear(prev_dim, num_classes))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class NoiseClassifierCNN(nn.Module):
    """1D CNN for noise classification from sequential features."""

    def __init__(self, input_dim, num_classes, num_channels=[64, 128, 256], kernel_size=3, dropout=0.3):
        """
        Initialize 1D CNN classifier.

        Args:
            input_dim: Input feature dimension
            num_classes: Number of output classes
            num_channels: List of channel dimensions for conv layers
            kernel_size: Kernel size for convolutions
            dropout: Dropout probability
        """
        super(NoiseClassifierCNN, self).__init__()

        self.input_dim = input_dim
        self.num_classes = num_classes

        # Convolutional layers
        conv_layers = []
        in_channels = 1  # Start with 1 channel

        for out_channels in num_channels:
            conv_layers.append(nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2))
            conv_layers.append(nn.BatchNorm1d(out_channels))
            conv_layers.append(nn.ReLU())
            conv_layers.append(nn.MaxPool1d(2))
            conv_layers.append(nn.Dropout(dropout))
            in_channels = out_channels

        self.conv_network = nn.Sequential(*conv_layers)

        # Calculate size after convolutions
        # Each MaxPool1d(2) reduces dimension by half
        reduced_dim = input_dim // (2 ** len(num_channels))
        fc_input_dim = num_channels[-1] * reduced_dim

        # Fully connected layers
        self.fc_network = nn.Sequential(
            nn.Linear(fc_input_dim, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        # Add channel dimension: (batch, features) -> (batch, 1, features)
        x = x.unsqueeze(1)

        # Convolutional layers
        x = self.conv_network(x)

        # Flatten
        x = x.view(x.size(0), -1)

        # Fully connected layers
        x = self.fc_network(x)

        return x


class NoiseClassifierEnsemble(nn.Module):
    """Ensemble of multiple classifiers for improved accuracy."""

    def __init__(self, input_dim, num_classes, num_models=3, hidden_dims=[256, 128, 64], dropout=0.3):
        """
        Initialize ensemble classifier.

        Args:
            input_dim: Input feature dimension
            num_classes: Number of output classes
            num_models: Number of models in ensemble
            hidden_dims: Hidden layer dimensions
            dropout: Dropout probability
        """
        super(NoiseClassifierEnsemble, self).__init__()

        self.models = nn.ModuleList([
            NoiseClassifierMLP(input_dim, num_classes, hidden_dims, dropout)
            for _ in range(num_models)
        ])

    def forward(self, x):
        # Get predictions from all models
        outputs = [model(x) for model in self.models]

        # Average predictions
        avg_output = torch.mean(torch.stack(outputs), dim=0)

        return avg_output


def create_data_loaders(features_file='features.npz', batch_size=32, test_size=0.2, random_state=42):
    """
    Create train and test data loaders from features file.

    Args:
        features_file: Path to features NPZ file
        batch_size: Batch size for training
        test_size: Fraction of data for testing
        random_state: Random seed

    Returns:
        train_loader, test_loader, train_dataset, test_dataset
    """
    # Load features
    data = np.load(features_file)
    features = data['features']
    labels = data['labels']

    print(f"Loaded {len(features)} samples with {features.shape[1]} features")
    print(f"Classes: {np.unique(labels)}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels,
        test_size=test_size,
        random_state=random_state,
        stratify=labels
    )

    print(f"Train set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Create datasets
    train_dataset = NoiseDataset(X_train, y_train, fit_transform=True)
    test_dataset = NoiseDataset(
        X_test, y_test,
        label_encoder=train_dataset.label_encoder,
        scaler=train_dataset.scaler,
        fit_transform=False
    )

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    return train_loader, test_loader, train_dataset, test_dataset


def save_model(model, label_encoder, scaler, filepath='noise_classifier.pth'):
    """
    Save model and preprocessing objects.

    Args:
        model: Trained PyTorch model
        label_encoder: Label encoder
        scaler: Feature scaler
        filepath: Output file path
    """
    torch.save({
        'model_state_dict': model.state_dict(),
        'model_class': model.__class__.__name__,
        'input_dim': model.input_dim,
        'num_classes': model.num_classes,
        'label_encoder': label_encoder,
        'scaler': scaler,
    }, filepath)

    print(f"✓ Model saved to {filepath}")


def load_model(filepath='noise_classifier.pth', device='cpu'):
    """
    Load model and preprocessing objects.

    Args:
        filepath: Model file path
        device: Device to load model on

    Returns:
        model, label_encoder, scaler
    """
    checkpoint = torch.load(filepath, map_location=device)

    # Recreate model
    model_class_name = checkpoint['model_class']
    input_dim = checkpoint['input_dim']
    num_classes = checkpoint['num_classes']

    if model_class_name == 'NoiseClassifierMLP':
        model = NoiseClassifierMLP(input_dim, num_classes)
    elif model_class_name == 'NoiseClassifierCNN':
        model = NoiseClassifierCNN(input_dim, num_classes)
    elif model_class_name == 'NoiseClassifierEnsemble':
        model = NoiseClassifierEnsemble(input_dim, num_classes)
    else:
        raise ValueError(f"Unknown model class: {model_class_name}")

    # Load weights
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    label_encoder = checkpoint['label_encoder']
    scaler = checkpoint['scaler']

    print(f"✓ Model loaded from {filepath}")
    print(f"  Input dim: {input_dim}")
    print(f"  Classes: {label_encoder.classes_}")

    return model, label_encoder, scaler


if __name__ == "__main__":
    print("=" * 80)
    print("NOISE CLASSIFIER MODEL - Architecture")
    print("=" * 80)

    # Example model creation
    input_dim = 200
    num_classes = 5

    print("\n1. MLP Classifier")
    print("─" * 80)
    mlp = NoiseClassifierMLP(input_dim, num_classes)
    print(mlp)
    print(f"\nTotal parameters: {sum(p.numel() for p in mlp.parameters()):,}")

    print("\n2. CNN Classifier")
    print("─" * 80)
    cnn = NoiseClassifierCNN(input_dim, num_classes)
    print(cnn)
    print(f"\nTotal parameters: {sum(p.numel() for p in cnn.parameters()):,}")

    print("\n3. Ensemble Classifier")
    print("─" * 80)
    ensemble = NoiseClassifierEnsemble(input_dim, num_classes, num_models=3)
    print(f"Ensemble of {len(ensemble.models)} models")
    print(f"Total parameters: {sum(p.numel() for p in ensemble.parameters()):,}")

    # Test forward pass
    print("\n4. Test Forward Pass")
    print("─" * 80)
    batch_size = 16
    test_input = torch.randn(batch_size, input_dim)

    with torch.no_grad():
        mlp_output = mlp(test_input)
        cnn_output = cnn(test_input)
        ensemble_output = ensemble(test_input)

    print(f"Input shape: {test_input.shape}")
    print(f"MLP output shape: {mlp_output.shape}")
    print(f"CNN output shape: {cnn_output.shape}")
    print(f"Ensemble output shape: {ensemble_output.shape}")

    print("\n✓ All models working correctly!")
