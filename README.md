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
- Last cumulative GPA
- Average precentage of absences
- TODO: data from Canvas

## Data

### Get Raw Data

Simply run the following command:

```bash
mlflow run ./src/data/get_data.py
```

The data will be saved in `data/raw/` folder.

## Model

- Decision Tree
- Gradient Boosting Decision Tree
