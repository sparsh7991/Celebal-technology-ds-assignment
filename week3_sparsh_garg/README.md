# Clustering Countries using Unsupervised Learning for HELP International

## 📌 Project Overview

This project aims to identify countries that require the highest priority for humanitarian aid using socio-economic and health indicators. The analysis is performed for **HELP International**, an NGO that has raised **$10 million** and wants to distribute the funds effectively among countries in need.

The project applies **unsupervised learning techniques** to group countries with similar characteristics and recommends the countries that should be prioritized.

---

## 🎯 Objective

- Analyze socio-economic and health indicators of different countries.
- Group countries using clustering techniques.
- Identify the least developed countries requiring immediate financial assistance.
- Rank countries within the most vulnerable cluster using a custom Priority Score.

---

## 📊 Dataset

The dataset contains **167 countries** with the following features:

- Country
- Child Mortality
- Exports
- Health Expenditure
- Imports
- Income
- Inflation
- Life Expectancy
- Total Fertility
- GDP per Capita

---

## 🛠 Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Scikit-learn

---

## 📈 Workflow

1. Data Loading
2. Data Inspection
3. Data Quality Check
4. Exploratory Data Analysis (EDA)
5. Feature Scaling
6. K-Means Clustering
7. Elbow Method
8. Silhouette Analysis
9. Cluster Profiling
10. Priority Score Calculation
11. DBSCAN Clustering
12. PCA Visualization
13. Final Recommendations

---

## 🤖 Machine Learning Algorithms

### K-Means Clustering
Used to group countries into clusters based on socio-economic and health indicators.

### DBSCAN
Applied as an alternative density-based clustering technique to compare clustering results and identify noise points.

### PCA (Principal Component Analysis)
Used to visualize the clusters in two dimensions.

---

## 📌 Results

- Countries were grouped into **4 clusters** using K-Means.
- Cluster profiling identified the least developed group based on:
  - High child mortality
  - Low income
  - Low GDP per capita
  - Low life expectancy
  - High fertility rate
- A custom **Priority Score** was created to rank countries within the most vulnerable cluster.

---

## 💡 Conclusion

The analysis provides a data-driven approach for HELP International to prioritize countries for humanitarian aid. By combining clustering techniques with socio-economic indicators, the project helps identify countries that require immediate financial support.

---

## 👨‍💻 Author

**Sparsh Garg**
