# Image Classification using ANN and CNN

This project compares the performance of **Artificial Neural Networks (ANN)** and **Convolutional Neural Networks (CNN)** for image classification using TensorFlow and Keras. The objective is to demonstrate why CNNs are more effective than ANNs for image-based tasks and to analyze the impact of various model improvements.

## Project Objectives

- Build and train an Artificial Neural Network (ANN) for image classification.
- Build and train a Convolutional Neural Network (CNN).
- Compare the performance of ANN and CNN using accuracy and loss metrics.
- Improve the ANN by increasing the number of hidden layers.
- Improve the CNN by training for more epochs, adding EarlyStopping, and applying data augmentation.
- Visualize and compare learning curves for both models.

## Technologies Used

- Python
- TensorFlow / Keras
- NumPy
- Matplotlib
- Pandas
- Jupyter Notebook

## Project Workflow

1. Load and preprocess the image dataset.
2. Normalize image pixel values.
3. Flatten images for the ANN model.
4. Build and train the ANN model.
5. Build and train the CNN model.
6. Enhance the ANN by increasing hidden layers.
7. Enhance the CNN using:
   - Data Augmentation
   - EarlyStopping
   - 20 Training Epochs
8. Evaluate all models on the test dataset.
9. Compare model performance using tables and learning curve visualizations.

## Model Architectures

### ANN
- Fully Connected (Dense) Layers
- ReLU Activation
- Dropout Regularization
- Softmax Output Layer

### CNN
- Convolution Layers (32 → 64 → 128 Filters)
- Batch Normalization
- Max Pooling
- Dense Layer
- Dropout
- Softmax Output Layer

## Performance Comparison

The models were evaluated using:
- Test Accuracy
- Test Loss
- Training Accuracy
- Validation Accuracy
- Training Loss
- Validation Loss

Learning curves were plotted to compare the convergence behavior of the improved ANN and the Augmented CNN.

## Key Observations

- CNN significantly outperformed the ANN in image classification.
- Increasing the ANN depth did not improve its performance considerably.
- Data augmentation improved the robustness of the CNN during training.
- EarlyStopping helped prevent unnecessary training and reduced the risk of overfitting.
- CNN learned spatial features effectively, resulting in better generalization.

## Repository Structure

```
├── Image_Classification.ipynb
├── README.md
└── images/ (optional)
```

## Conclusion

This project demonstrates that Convolutional Neural Networks (CNNs) are more suitable than Artificial Neural Networks (ANNs) for image classification tasks. CNNs achieve better accuracy by automatically learning spatial and hierarchical features from images, whereas ANNs lose spatial information by flattening the input images.

## Author

**Sparsh Garg**
