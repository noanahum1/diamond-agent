import pandas as pd

# Show all columns without truncating
pd.set_option('display.max_columns', None)
# Widen the display so columns don't wrap to the next line
pd.set_option('display.width', 1000)

# Define the file path
file_path_1 = 'diamonds1.csv'

# 1. Load the data
print("--- Loading the first dataset (diamonds1.csv) ---")
try:
    df_diamonds = pd.read_csv(file_path_1)
    print("File loaded successfully! Dataset shape (rows, columns):", df_diamonds.shape)
except FileNotFoundError:
    print(f"Error: The file {file_path_1} could not be found. Please ensure it is in the same directory as this script.")
    exit()
print("\n")

# 2. Preview the data (first 5 rows)
print("--- Data Preview ---")
print(df_diamonds.head())
print("\n")

# 3. Check column types and general information
print("--- General Information (info) ---")
df_diamonds.info()
print("\n")

# 4. Descriptive statistics (mean, std, min, max)
print("--- Descriptive Statistics (describe) ---")
print(df_diamonds.describe())
print("\n")

# 5. Check for missing values (Nulls)
print("--- Missing Values Check ---")
print(df_diamonds.isnull().sum())
print("\n")

# 6. Check for duplicate rows
print("--- Duplicate Rows Check ---")
duplicates_diamonds = df_diamonds.duplicated().sum()
print(f"Found {duplicates_diamonds} duplicate rows in the first dataset.")
print("\n")


print("--- Starting Data Transformation ---")
print("--- Checking for Zero Values in Dimensions ---")
# Count how many times 0 appears in each specific column
zeros_in_x = (df_diamonds['x'] == 0).sum()
zeros_in_y = (df_diamonds['y'] == 0).sum()
zeros_in_z = (df_diamonds['z'] == 0).sum()
print(f"Number of rows where x (length) is 0: {zeros_in_x}")
print(f"Number of rows where y (width) is 0: {zeros_in_y}")
print(f"Number of rows where z (depth) is 0: {zeros_in_z}")

# Count total unique rows that have at least one zero in x, y, or z
total_zero_rows = len(
    df_diamonds[ (df_diamonds['x'] == 0) | (df_diamonds['y'] == 0) | (df_diamonds['z'] == 0)])
print(f"\nTotal unique rows with at least one zero dimension: {total_zero_rows}")
print("\n--- Data Cleaning: Deleting Rows with Zero Dimensions ---")

# Print original shape
print(f"Original dataset shape: {df_diamonds.shape}")

# Find the indices of rows where x, y, or z is 0
indices_to_drop = df_diamonds[ (df_diamonds['x'] == 0) | (df_diamonds['y'] == 0) | (df_diamonds['z'] == 0)].index

print(f"Found {len(indices_to_drop)} rows to drop.")

# Drop the rows
df_diamonds.drop(indices_to_drop, inplace=True)

# Print new shape
print(f"New dataset shape after cleaning: {df_diamonds.shape}")

# Verify no zero values remain
zeros_left = len(
    df_diamonds[ (df_diamonds['x'] == 0) | (df_diamonds['y'] == 0) | (df_diamonds['z'] == 0)])
print(f"Verification - Total zero dimension rows remaining: {zeros_left}")
# Save the cleaned DataFrame back to the CSV file
df_diamonds.to_csv("diamonds1.csv", index=False)
print("\nCleaned file has been saved successfully.")

# Mapping dictionaries
cut_mapping = { 'Fair': 1, 'Good': 2, 'Very Good': 3, 'Premium': 4, 'Ideal': 5}
color_mapping = { 'J': 1, 'I': 2, 'H': 3, 'G': 4, 'F': 5, 'E': 6, 'D': 7}
clarity_mapping = { 'I1': 1, 'SI2': 2, 'SI1': 3, 'VS2': 4, 'VS1': 5, 'VVS2': 6, 'VVS1': 7, 'IF': 8}

# Creating new encoded columns
df_diamonds['cut_encoded'] = df_diamonds['cut'].map(cut_mapping)
df_diamonds['color_encoded'] = df_diamonds['color'].map(color_mapping)
df_diamonds['clarity_encoded'] = df_diamonds['clarity'].map(clarity_mapping)

df_diamonds.to_csv("diamonds1.csv", index=False)
print("\nNew encoded columns added successfully.")

df_diamonds['carat_category'] = pd.cut(df_diamonds['carat'],
        bins=[0,0.5,1,1.5,2,2.5,3,df_diamonds['carat'].max()],
        labels=['extra extra small','extra small','small','medium','large','extra large','ultra large (3+)'])
df_diamonds.to_csv("diamonds1.csv", index=False)

carat_category_mapping = {'extra extra small':1, 'extra small':2, 'small':3, 'medium':4, 'large':5, 'extra large':6, 'ultra large (3+)':7}
df_diamonds['carat_category_encoded'] = df_diamonds['carat_category'].map(carat_category_mapping)
print("Numeric carat category column added.")
df_diamonds.to_csv("diamonds1.csv", index=False)
print("File updated successfully.")

print("\n--- Creating Price Categories ---")
df_diamonds['price_category'] = pd.qcut(
    df_diamonds['price'], q=5, labels=['very low', 'low', 'medium', 'high', 'very high'])
print("Price category column added successfully.")
price_category_mapping = {'very low': 1, 'low': 2, 'medium': 3, 'high': 4, 'very high': 5}
df_diamonds['price_category_encoded'] = df_diamonds['price_category'].map(price_category_mapping)
print("Encoded price category column added successfully.")
df_diamonds.to_csv("diamonds1.csv", index=False)
print("File updated successfully with price category columns.")
