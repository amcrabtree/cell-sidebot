import pandas as pd
import numpy as np

# Define the number of images, ROIs, and classes
images = ['Slide_1', 'Slide_2', 'Slide_3', 'Slide_4', 'Slide_5', 'Slide_6']
parents = ['ROI_01', 'ROI_02', 'ROI_03']
cell_types = ['EPI', 'CTOX', 'B', 'TREG', 'HELPER', 'MAC', 'DC']

# Number of cells per ROI per image
cells_per_roi = 1000

# Define probabilities for each cell type per Slide
probabilities = {
    'Slide_1': [0.05, 0.5, 0.1, 0.1, 0.1, 0.05, 0.1],  # Higher proportion of CTOX
    'Slide_2': [0.05, 0.05, 0.15, 0.15, 0.2, 0.3, 0.1], # Lower proportion of CTOX
    'Slide_3': [0.05, 0.4, 0.1, 0.1, 0.1, 0.15, 0.1],  # Higher proportion of CTOX
    'Slide_4': [0.05, 0.45, 0.1, 0.1, 0.1, 0.1, 0.1],  # Higher proportion of CTOX
    'Slide_5': [0.1, 0.1, 0.2, 0.15, 0.15, 0.2, 0.1],  # Lower proportion of CTOX
    'Slide_6': [0.1, 0.1, 0.15, 0.15, 0.15, 0.25, 0.1]  # Lower proportion of CTOX
}

# Function to generate the Name column based on conditions
def generate_name_column(row):
    if row['Class'] == 'EPI' and row['Image'] in ['Slide_1', 'Slide_3', 'Slide_4']:
        return np.random.choice(['Ki67', ''], p=[0.7, 0.3])  # Higher chance of "Ki67"
    else:
        return np.random.choice(['Ki67', ''], p=[0.1, 0.9])  # Lower chance of "Ki67"

# Generate the data
data = {
    'Image': np.repeat(images, len(parents) * cells_per_roi),
    'Parent': np.tile(np.repeat(parents, cells_per_roi), len(images)),
    'Class': np.hstack([
        np.random.choice(cell_types, size=cells_per_roi * len(parents), p=probabilities[image])
        for image in images
    ])
}

# Create the DataFrame
df = pd.DataFrame(data)

# Apply the function to generate the Name column
df['Name'] = df.apply(generate_name_column, axis=1)

# Save to file
df.to_csv("test/cell_data.txt", sep="\t", index=False)