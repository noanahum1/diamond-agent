import pandas as pd
from pathlib import Path

# Show all columns without truncating
pd.set_option('display.max_columns', None)
# Widen the display so columns don't wrap to the next line
pd.set_option('display.width', 1000)

# Define the file path
BASE_DIR = Path(__file__).resolve().parent
file_path_2 = BASE_DIR / "diamonds2.csv"

# 1. Load the data
print("--- Loading the second dataset (diamonds2.csv) ---")
try:
    df_diamonds_cleaned = pd.read_csv(file_path_2)
    print("File loaded successfully! Dataset shape (rows, columns):", df_diamonds_cleaned.shape)
except FileNotFoundError:
    print(f"Error: The file {file_path_2} could not be found. Please ensure it is in the same directory as this script.")
    exit()
print("\n")

# 2. Preview the data (first 5 rows)
print("--- Data Preview ---")
print(df_diamonds_cleaned.head())
print("\n")

# 3. Check column types and general information
print("--- General Information (info) ---")
df_diamonds_cleaned.info()
print("\n")

# 4. Descriptive statistics (mean, std, min, max)
print("--- Descriptive Statistics (describe) ---")
print(df_diamonds_cleaned.describe())
print("\n")

# 5. Check for missing values (Nulls)
print("--- Missing Values Check ---")
print(df_diamonds_cleaned.isnull().sum())
print("\n")

# 6. Check for duplicate rows
print("--- Duplicate Rows Check ---")
duplicates_diamonds_cleaned = df_diamonds_cleaned.duplicated().sum()
print(f"Found {duplicates_diamonds_cleaned} duplicate rows in the second dataset.")
print("\n")


print("--- Starting Data Transformation ---")
# Remove duplicate rows while keeping the first occurrence
df_diamonds_cleaned.drop_duplicates(inplace=True)
print("Duplicate rows removed (keeping first occurrence).")
# Save the updated DataFrame back to the original CSV file
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("File updated successfully.")

total_zero_rows = df_diamonds_cleaned[
    (df_diamonds_cleaned['Length'] <= 0) |
    (df_diamonds_cleaned['Width'] <= 0) |
    (df_diamonds_cleaned['Height'] <= 0)]
print("Total rows with at least one zero dimension:", len(total_zero_rows))

# Create a new price category column with 5 groups based on quantiles
df_diamonds_cleaned['price_category'] = pd.qcut(
    df_diamonds_cleaned['Price'],
    q=5, labels=['very low', 'low', 'medium', 'high', 'very high'])

print("Price category column added successfully.")
# Map the price categories to ordinal numeric values
price_category_mapping = { 'very low': 1, 'low': 2, 'medium': 3, 'high': 4, 'very high': 5}

# Create a new encoded numeric column
df_diamonds_cleaned['price_category_encoded'] = df_diamonds_cleaned['price_category'].map(price_category_mapping)
print("Encoded price category column added successfully.")

# Save the updated DataFrame back to the original CSV file
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("File updated successfully.")


# Print shape before cleaning
print("Shape before removing missing rows:", df_diamonds_cleaned.shape)

# Clean and standardize Cut, Color, Clarity columns
for col in ['Cut', 'Color', 'Clarity']:
    # Remove leading/trailing spaces only from existing string values
    df_diamonds_cleaned[col] = df_diamonds_cleaned[col].str.strip()

    # Convert empty strings / spaces-only / Unknown / nan-like strings to real missing values
    df_diamonds_cleaned[col] = df_diamonds_cleaned[col].replace(r'^\s*$', pd.NA, regex=True)
    df_diamonds_cleaned[col] = df_diamonds_cleaned[col].replace(
        ['Unknown', 'unknown', 'nan', 'NaN', 'NAN', 'None', 'none'],pd.NA)

# Print missing values before dropping rows
print("\nMissing values in Cut, Color, Clarity before dropna:")
print(df_diamonds_cleaned[['Cut', 'Color', 'Clarity']].isnull().sum())

# Remove rows with missing values in the three columns
df_diamonds_cleaned = df_diamonds_cleaned.dropna(subset=['Cut', 'Color', 'Clarity']).copy()

# Print shape after cleaning
print("Shape after removing missing rows:", df_diamonds_cleaned.shape)

# Mapping dictionaries (diamond standard order)
cut_mapping = {'Fair': 1,'Good': 2,'Very Good': 3,'Excellent': 4,'Ideal': 5,'Astor': 6}
color_mapping = {'J': 1,'I': 2,'H': 3,'G': 4,'F': 5,'E': 6,'D': 7}
clarity_mapping = {'I1': 1, 'SI2': 2, 'SI1': 3, 'VS2': 4, 'VS1': 5, 'VVS2': 6, 'VVS1': 7, 'IF': 8, 'FL': 9}

# Create encoded columns
df_diamonds_cleaned['Cut_encoded'] = df_diamonds_cleaned['Cut'].map(cut_mapping)
df_diamonds_cleaned['Color_encoded'] = df_diamonds_cleaned['Color'].map(color_mapping)
df_diamonds_cleaned['Clarity_encoded'] = df_diamonds_cleaned['Clarity'].map(clarity_mapping)

print("\nEncoded columns added successfully.")

# Check if there are values that were not encoded
print("\nNumber of missing values in encoded columns:")
print(df_diamonds_cleaned[['Cut_encoded', 'Color_encoded', 'Clarity_encoded']].isnull().sum())

# Optional: show problematic values if encoding failed
print("\nUnmapped values in Cut:")
print(df_diamonds_cleaned.loc[df_diamonds_cleaned['Cut_encoded'].isnull(), 'Cut'].unique())

print("\nUnmapped values in Color:")
print(df_diamonds_cleaned.loc[df_diamonds_cleaned['Color_encoded'].isnull(), 'Color'].unique())

print("\nUnmapped values in Clarity:")
print(df_diamonds_cleaned.loc[df_diamonds_cleaned['Clarity_encoded'].isnull(), 'Clarity'].unique())

# Save back to the ORIGINAL CSV file (overwrite)
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("\nOriginal CSV file updated successfully.")

# --- Clean spaces in categorical columns ---
df_diamonds_cleaned['Polish'] = df_diamonds_cleaned['Polish'].astype(str).str.strip()
df_diamonds_cleaned['Symmetry'] = df_diamonds_cleaned['Symmetry'].astype(str).str.strip()
df_diamonds_cleaned['Girdle'] = df_diamonds_cleaned['Girdle'].astype(str).str.strip()

# --- Mapping dictionaries ---
polish_mapping = {'Fair':1, 'Good':2, 'Very Good':3, 'Excellent':4, 'Ideal':5}
symmetry_mapping = {'Fair':1, 'Good':2, 'Very Good':3, 'Excellent':4, 'Ideal':5}
girdle_mapping = {'Extremely Thin':1, 'Very Thin':2, 'Thin':3, 'Medium':4, 'Slightly Thick':5, 'Thick':6, 'Very Thick':7, 'Extremely Thick':8, 'Medium to Slightly Thick':4.5, 'Medium to Thick':5, 'Medium to Very Thick':6, 'Slightly Thick to Thick':5.5, 'Slightly Thick to Very Thick':6.5, 'Thick to Very Thick':6.5, 'Thin to Medium':3.5, 'Thin to Slightly Thick':4, 'Thin to Thick':4.5, 'Thin to Very Thick':5.5, 'Very Thin to Slightly Thick':3, 'Very Thin to Thin':2.5, 'Very Thin to Very Thick':4.5, 'Very Thin to Thick':4}

# --- Create encoded columns ---
df_diamonds_cleaned['Polish_encoded'] = df_diamonds_cleaned['Polish'].map(polish_mapping)
df_diamonds_cleaned['Symmetry_encoded'] = df_diamonds_cleaned['Symmetry'].map(symmetry_mapping)
df_diamonds_cleaned['Girdle_encoded'] = df_diamonds_cleaned['Girdle'].map(girdle_mapping)
print("Polish, Symmetry, and Girdle encoded successfully.")

# --- Save updated dataset back to original CSV ---
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("File updated successfully.")

# --- Drop Culet and Fluorescence columns safely ---
columns_to_drop = ['Culet', 'Fluorescence']
existing_columns = [col for col in columns_to_drop if col in df_diamonds_cleaned.columns]
df_diamonds_cleaned.drop(columns=existing_columns, inplace=True)
print(f"Columns removed successfully: {existing_columns}")

# --- Save updated dataset back to original CSV ---
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("File updated successfully.")

# Total number of rows
total_rows = df_diamonds_cleaned.shape[0]
print(f"Total rows in dataset: {total_rows}")
# Boolean mask for rows with at least one missing value
rows_with_missing = df_diamonds_cleaned.isnull().any(axis=1)
# Number of rows that will be affected (deleted)
num_rows_to_drop = rows_with_missing.sum()
print(f"\nNumber of rows that contain at least one missing value: {num_rows_to_drop}")

# Percentage of affected rows
percentage = (num_rows_to_drop / total_rows) * 100
print(f"Percentage of dataset that will be removed: {percentage:.4f}%")

# Total number of missing values in dataset
total_missing_values = df_diamonds_cleaned.isnull().sum().sum()
print(f"\nTotal number of missing values in dataset: {total_missing_values}")

print("Shape before removing missing values:", df_diamonds_cleaned.shape)
# Remove all rows that contain at least one missing value
df_diamonds_cleaned = df_diamonds_cleaned.dropna().copy()
print("Shape after removing missing values:", df_diamonds_cleaned.shape)
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("File updated successfully after removing missing values.")


# Rename Carat Weight column to Carat
df_diamonds_cleaned.rename(columns={'Carat Weight': 'Carat'}, inplace=True)

# Create Carat categories
df_diamonds_cleaned['Carat_category'] = pd.cut(
    df_diamonds_cleaned['Carat'],
    bins=[0, 0.5, 1, 1.5, 2, 2.5, 3, df_diamonds_cleaned['Carat'].max()],
    labels=['extra extra small', 'extra small', 'small', 'medium', 'large', 'extra large', 'ultra large (3+)'])
# Map Carat categories to numeric values
carat_category_mapping = {'extra extra small': 1, 'extra small': 2, 'small': 3, 'medium': 4, 'large': 5, 'extra large': 6,
                          'ultra large (3+)': 7}
df_diamonds_cleaned['Carat_category_encoded'] = df_diamonds_cleaned['Carat_category'].map(carat_category_mapping)
df_diamonds_cleaned.to_csv(file_path_2, index=False)
print("Carat column renamed, categories created, and encoded successfully.")