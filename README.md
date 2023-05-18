# End-to-End Student Dropouts Prediction


## Features

### Demographics

- Age
- Gender
- Ethnicity

### Academic

- Full time status
- First generation
- Number of credits is attemtping
- Number of courses retaken
- New student or not
- Number of developmental math courses
- Number of developmental english courses
- Course modularity
- Past dropout rate
- Dropout history for the last 3 semesters
- High school GPA if a student is new to college
- Last term cumulative GPA
- ~~Last term GPA~~
- Average precentage of absences
- TODO: data from Canvas

## Data

### Get Raw Data

Simply run the following command:

```bash
mlflow run ./src/get_data/
```

The data will be saved in `data/raw/` folder.


### Preprocess Data

To get the preprocessed data for week 10, simply run the following command:

```bash
mlflow run ./src/preprocess/ -P week_number=10
```

The preprocessed data named `cleaned-10.csv` will be saved in `data/processed/` folder.

## Model

- Decision Tree
- Gradient Boosting Decision Tree
