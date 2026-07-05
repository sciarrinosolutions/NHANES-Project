"""
Central registry for all five blood tests.

Each entry in TESTS defines:
  - key:        internal identifier used in URLs, form fields, and pkl filenames
  - label:      human-readable name shown in the UI
  - description: one-line description shown in the test selection sidebar
  - features:   ordered list of feature names this model expects, in the exact
                column order the scaler/imputer/model was trained on

The QUESTIONS dict maps each unique feature name to its display metadata.
This is the single place to update question text, input type, choices, etc.
"""

# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

TESTS = [
    {
        'key': 'hscrp',
        'label': 'hsCRP',
        'full_label': 'High-Sensitivity C-Reactive Protein',
        'description': 'A marker of systemic inflammation',
        'features': [
            'bmi',
            'pulse',
            'difficulty_walking_climbing_steps',
            'self_rated_health',
            'map',
            'urinary_leakage_frequency',
            'times_per_night_urinating',
            'protein',
            'romberg_avg_time',
            'fiber',
            'income_poverty_ratio',
            'num_rx_drugs',
        ],
    },
    {
        'key': 'hba1c',
        'label': 'HbA1c',
        'full_label': 'Hemoglobin A1c',
        'description': 'A measure of average blood sugar over 3 months',
        'features': [
            'age_years',
            'bmi',
            'oral_health',
            'race_ethnicity',
            'map',
            'self_rated_health',
            'taking_aspirin',
            'freq_worried_nervous_anxious',
            'chol_diet',
            'income_poverty_ratio',
            'romberg_avg_time',
            'drinks_per_week',
            'taking_bp_medication',
        ],
    },
    {
        'key': 'vitamin_d',
        'label': 'Vitamin D',
        'full_label': 'Vitamin D',
        'description': 'Supports bone health and immune function',
        'features': [
            'age_years',
            'race_ethnicity',
            'bmi',
            'sedentary_time_per_day',
            'pulse',
            'food_security_category',
            'num_smokers_in_household',
            'freq_use_sunscreen',
            'income_poverty_ratio',
            'current_smoker_status',
            'caff',
            'fiber',
            'exam_season',
        ],
    },
    {
        'key': 'wbc',
        'label': 'White Blood Cell Count',
        'full_label': 'White Blood Cell Count',
        'description': 'An indicator of immune system activity',
        'features': [
            'pulse',
            'bmi',
            'num_rx_drugs',
            'self_rated_health',
            'fiber',
            'income_poverty_ratio',
            'romberg_avg_time',
            'current_smoker_status',
            'age_years',
            'smoked_tobacco_past_5_days',
        ],
    },
    {
        'key': 'hdl',
        'label': 'HDL Cholesterol',
        'full_label': 'HDL (Good) Cholesterol',
        'description': 'The protective form of cholesterol',
        'features': [
            'bmi',
            'pulse',
            'self_rated_health',
            'food_security_category',
            'ate_fish_past_30_days',
            'sug_diet',
            'caff',
            'income_poverty_ratio',
            'age_years',
            'drinks_per_week',
        ],
    },
]

# ---------------------------------------------------------------------------
# Question registry
# Each key matches a feature name used in TESTS above.
# 'type' options: 'bmi_inputs', 'number', 'radio', 'select', 'binary_radio', 'season'
# ---------------------------------------------------------------------------

QUESTIONS = {

    # --- Shared: BMI (computed from height + weight) ---
    'bmi': {
        'label': 'Height and Weight',
        'question': 'What is your height and weight?',
        'hint': 'Your BMI will be calculated automatically as you type.',
        'type': 'bmi_inputs',
    },

    # --- Shared: Age ---
    'age_years': {
        'label': 'Age',
        'question': 'What is your age?',
        'hint': 'Enter your age in whole years.',
        'type': 'number',
        'attrs': {'min': 18, 'max': 85, 'step': 1},
    },

    # --- Shared: Pulse (categorical) ---
    'pulse': {
        'label': 'Resting Heart Rate',
        'question': 'How would you describe your resting heart rate (pulse)?',
        'hint': 'Select the range that best matches your resting pulse. You can check this with a finger on your wrist for 60 seconds, or with a smartwatch.',
        'type': 'radio',
        'choices': [
            (45,  'Very slow — below 50 bpm'),
            (55,  'Slow — 50 to 60 bpm'),
            (70,  'Normal — 61 to 80 bpm'),
            (90,  'Elevated — 81 to 100 bpm'),
            (110, 'High — above 100 bpm'),
        ],
    },

    # --- Shared: Self-rated health ---
    'self_rated_health': {
        'label': 'Overall Health',
        'question': 'How would you rate your overall health?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Excellent'),
            (2, 'Very Good'),
            (3, 'Good'),
            (4, 'Fair'),
            (5, 'Poor'),
        ],
    },

    # --- Shared: MAP (5-category radio, values are MAP midpoints in mmHg) ---
    'map': {
        'label': 'Blood Pressure',
        'question': 'How would you describe your typical blood pressure?',
        'hint': (
            'If you know your numbers, use this guide: '
            'Very Low = below 70 MAP (e.g. 90/55 reading), '
            'Low = 70-80 MAP (e.g. 100/65), '
            'Normal = 81-93 MAP (e.g. 120/80), '
            'High = 94-106 MAP (e.g. 140/90), '
            'Very High = above 106 MAP (e.g. 160/100+). '
            'MAP = (systolic + 2 x diastolic) / 3.'
        ),
        'type': 'radio',
        'choices': [
            (65,  'Very Low — typically below 70 mmHg MAP (e.g. 90/55)'),
            (75,  'Low — typically 70 to 80 mmHg MAP (e.g. 100/65)'),
            (87,  'Normal — typically 81 to 93 mmHg MAP (e.g. 120/80)'),
            (100, 'High — typically 94 to 106 mmHg MAP (e.g. 140/90)'),
            (115, 'Very High — typically above 106 mmHg MAP (e.g. 160/100 or higher)'),
        ],
    },

    # --- Shared: Income / poverty ratio ---
    'income_poverty_ratio': {
        'label': 'Household Financial Situation',
        'question': 'How would you describe your household\'s financial situation?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (0.5, 'Struggling to meet basic needs'),
            (1.5, 'Just getting by'),
            (3.0, 'Comfortable'),
            (5.0, 'Well-off'),
        ],
    },

    # --- Shared: Romberg / balance ---
    'romberg_avg_time': {
        'label': 'Balance and Steadiness',
        'question': 'How would you rate your balance when standing or walking?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (5,  'Very poor — I frequently lose balance or feel unsteady'),
            (10, 'Poor — I often feel unsteady or need support'),
            (18, 'Fair — I occasionally feel unsteady but manage without support'),
            (25, 'Good — I rarely feel unsteady'),
            (30, 'Excellent — I have no issues with balance'),
        ],
    },

    # --- Shared: Fiber intake ---
    'fiber': {
        'label': 'Daily Fiber Intake',
        'question': 'On average, how much dietary fiber do you consume per day?',
        'hint': 'Fiber is found in fruits, vegetables, beans, whole grains, nuts, and seeds. One serving is roughly 5 grams.',
        'type': 'radio',
        'choices': [
            (2,  'Very low — rarely or none (less than 5g per day)'),
            (5,  'Low — about 1 serving per day (around 5g)'),
            (12, 'Moderate — about 2 to 3 servings per day (10 to 15g)'),
            (22, 'High — about 4 to 5 servings per day (20 to 25g)'),
            (35, 'Very high — 6 or more servings per day (over 30g)'),
        ],
    },

    # --- Shared: Caffeine intake ---
    'caff': {
        'label': 'Daily Caffeine Intake',
        'question': 'On average, how much caffeine do you consume per day?',
        'hint': 'One serving is roughly 100mg — about one standard cup of coffee.',
        'type': 'radio',
        'choices': [
            (25,  'Very low — rarely or none (less than 50mg per day, e.g. decaf only)'),
            (100, 'Low — about 1 serving per day (around 100mg, e.g. 1 coffee)'),
            (250, 'Moderate — about 2 to 3 servings per day (200 to 300mg)'),
            (450, 'High — about 4 to 5 servings per day (400 to 500mg)'),
            (650, 'Very high — 6 or more servings per day (over 600mg)'),
        ],
    },

    # --- Shared: Drinks per week ---
    'drinks_per_week': {
        'label': 'Alcoholic Drinks Per Week',
        'question': 'On average, how many alcoholic drinks do you consume per week?',
        'hint': 'Enter a whole number. Enter 0 if you do not drink.',
        'type': 'number',
        'attrs': {'min': 0, 'max': 70, 'step': 1},
    },

    # --- Shared: Race / ethnicity (single question, split into two dummies in view) ---
    'race_ethnicity': {
        'label': 'Race and Ethnicity',
        'question': 'Which of the following best describes your race and Hispanic origin?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Mexican American'),
            (2, 'Other Hispanic'),
            (3, 'Non-Hispanic White'),
            (4, 'Non-Hispanic Black'),
            (6, 'Non-Hispanic Asian'),
            (7, 'Other Race or Multiracial'),
        ],
    },

    # --- Shared: Food security ---
    'food_security_category': {
        'label': 'Household Food Security',
        'question': 'Which best describes your household\'s access to food over the past 12 months?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Full food security — always able to afford enough food'),
            (2, 'Marginal food security — occasionally worried about food or ran short'),
            (3, 'Low food security — reduced quality or variety of food but not reduced intake'),
            (4, 'Very low food security — reduced food intake due to lack of money'),
        ],
    },

    # --- HSCRP only ---
    'difficulty_walking_climbing_steps': {
        'label': 'Walking and Climbing',
        'question': 'How much difficulty do you have walking or climbing steps without special equipment?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'No difficulty'),
            (2, 'Some difficulty'),
            (3, 'Much difficulty'),
            (4, 'Unable to do'),
        ],
    },

    'urinary_leakage_frequency': {
        'label': 'Urinary Leakage',
        'question': 'In the past 12 months, how often have you experienced accidental leakage of urine?',
        'hint': 'This includes any unintentional loss of urine, even a small amount.',
        'type': 'radio',
        'choices': [
            (1, 'Never'),
            (2, 'Less than once a month'),
            (3, 'A few times a month'),
            (4, 'A few times a week'),
            (5, 'Every day and/or night'),
        ],
    },

    'times_per_night_urinating': {
        'label': 'Nighttime Urination',
        'question': 'On a typical night, how many times do you get up to urinate?',
        'hint': 'Enter a whole number. Enter 0 if you do not get up at night.',
        'type': 'number',
        'attrs': {'min': 0, 'max': 10, 'step': 1},
    },

    'protein': {
        'label': 'Daily Protein Intake',
        'question': 'On average, how much protein do you consume per day?',
        'hint': 'One serving is roughly 25 grams — about the amount in a chicken breast or a cup of Greek yogurt.',
        'type': 'radio',
        'choices': [
            (12,  'Very low — rarely or none (less than 25g per day)'),
            (25,  'Low — about 1 serving per day (around 25g)'),
            (62,  'Moderate — about 2 to 3 servings per day (50 to 75g)'),
            (100, 'High — about 4 servings per day (around 100g)'),
            (137, 'Very high — 5 or more servings per day (over 125g)'),
        ],
    },

    'num_rx_drugs': {
        'label': 'Prescription Medications',
        'question': 'How many different prescription medications are you currently taking?',
        'hint': 'Count only medications prescribed by a doctor. Do not count over-the-counter supplements or vitamins.',
        'type': 'number',
        'attrs': {'min': 0, 'max': 20, 'step': 1},
    },

    # --- HbA1c only ---
    'oral_health': {
        'label': 'Oral Health',
        'question': 'How would you rate the health of your teeth and gums?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Excellent'),
            (2, 'Very Good'),
            (3, 'Good'),
            (4, 'Fair'),
            (5, 'Poor'),
        ],
    },

    'taking_aspirin': {
        'label': 'Aspirin Use',
        'question': 'Are you currently taking aspirin on a regular basis?',
        'hint': 'This includes both prescription and over-the-counter aspirin taken regularly.',
        'type': 'binary_radio',
        'choices': [
            (1, 'Yes'),
            (0, 'No'),
        ],
    },

    'freq_worried_nervous_anxious': {
        'label': 'Anxiety Frequency',
        'question': 'How often do you feel worried, nervous, or anxious?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Daily'),
            (2, 'Weekly'),
            (3, 'Monthly'),
            (4, 'A few times a year'),
            (5, 'Never'),
        ],
    },

    'chol_diet': {
        'label': 'Daily Dietary Cholesterol',
        'question': 'On average, how much cholesterol do you consume through food per day?',
        'hint': 'One serving is roughly 200mg — about the amount in one large egg.',
        'type': 'radio',
        'choices': [
            (50,  'Very low — rarely or none (less than 100mg per day)'),
            (200, 'Low — about 1 serving per day (around 200mg)'),
            (400, 'Moderate — about 2 servings per day (around 400mg)'),
            (600, 'High — about 3 servings per day (around 600mg)'),
            (800, 'Very high — 4 or more servings per day (over 800mg)'),
        ],
    },

    'taking_bp_medication': {
        'label': 'Blood Pressure Medication',
        'question': 'Are you currently taking any medication to treat high blood pressure?',
        'hint': '',
        'type': 'binary_radio',
        'choices': [
            (1, 'Yes'),
            (0, 'No'),
        ],
    },

    # --- Vitamin D only ---
    'sedentary_time_per_day': {
        'label': 'Daily Sedentary Time',
        'question': 'On a typical day, how many hours do you spend sitting or doing sedentary activities?',
        'hint': 'Include time watching TV, working at a desk, riding in a car, and similar activities. Enter a number between 0 and 24.',
        'type': 'number',
        'attrs': {'min': 0, 'max': 24, 'step': 0.5},
        'convert': 'hours_to_minutes',
    },

    'num_smokers_in_household': {
        'label': 'Smokers in Household',
        'question': 'How many people in your household currently smoke cigarettes inside the home?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (0, 'No one smokes inside the home'),
            (1, '1 household member smokes inside the home'),
            (2, '2 or more household members smoke inside the home'),
        ],
    },

    'freq_use_sunscreen': {
        'label': 'Sunscreen Use',
        'question': 'When going outside on a sunny day, how often do you use sunscreen?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Always'),
            (2, 'Most of the time'),
            (3, 'Sometimes'),
            (4, 'Rarely'),
            (5, 'Never'),
        ],
    },

    'current_smoker_status': {
        'label': 'Current Smoking Status',
        'question': 'Do you currently smoke cigarettes?',
        'hint': '',
        'type': 'radio',
        'choices': [
            (1, 'Yes, every day'),
            (2, 'Yes, some days'),
            (3, 'No, not at all'),
        ],
    },

    'exam_season': {
        'label': 'Current Season',
        'question': 'What is the current season where you live?',
        'hint': 'This is used to account for seasonal variation in Vitamin D levels.',
        'type': 'season',
        'choices': [
            (0, 'Winter or Spring (November through April)'),
            (1, 'Summer or Fall (May through October)'),
        ],
    },

    # --- WBC only ---
    'smoked_tobacco_past_5_days': {
        'label': 'Recent Tobacco Use',
        'question': 'In the past 5 days, have you smoked any tobacco products?',
        'hint': 'This includes cigarettes, cigars, pipes, or any other tobacco product.',
        'type': 'binary_radio',
        'choices': [
            (1, 'Yes'),
            (0, 'No'),
        ],
    },

    # --- HDL only ---
    'ate_fish_past_30_days': {
        'label': 'Fish or Shellfish Intake',
        'question': 'In the past 30 days, did you eat any fish or shellfish?',
        'hint': '',
        'type': 'binary_radio',
        'choices': [
            (1, 'Yes'),
            (0, 'No'),
        ],
    },

    'sug_diet': {
        'label': 'Daily Sugar Intake',
        'question': 'On average, how much added sugar do you consume per day?',
        'hint': 'One serving is roughly 25 grams — about the amount in a can of soda.',
        'type': 'radio',
        'choices': [
            (6,   'Very low — rarely or none (less than 12g per day)'),
            (25,  'Low — about 1 serving per day (around 25g)'),
            (50,  'Moderate — about 2 servings per day (around 50g)'),
            (75,  'High — about 3 servings per day (around 75g)'),
            (112, 'Very high — 4 or more servings per day (over 100g)'),
        ],
    },
}


def get_question_order(selected_test_keys):
    """
    Given a list of selected test keys, return the ordered list of unique
    feature names that need to appear in the survey.

    Order is determined by the order features appear in TESTS, walking through
    each selected test in display order. A feature is added only the first time
    it is encountered.
    """
    seen = set()
    ordered = []
    for test in TESTS:
        if test['key'] not in selected_test_keys:
            continue
        for feature in test['features']:
            if feature not in seen:
                seen.add(feature)
                ordered.append(feature)
    return ordered
