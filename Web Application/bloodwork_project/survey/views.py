import json
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .tests_config import TESTS, QUESTIONS, get_question_order
from .forms import TestSelectionForm, build_survey_form
from .prediction import run_all_predictions


def index(request):
    """Landing page: test selection."""
    form = TestSelectionForm()
    return render(request, 'survey/index.html', {
        'form': form,
        'tests': TESTS,
    })


@require_http_methods(['POST'])
def start_survey(request):
    """
    Handles test selection form submission.
    Validates selected tests, then renders the survey page.
    """
    form = TestSelectionForm(request.POST)
    if not form.is_valid():
        return render(request, 'survey/index.html', {
            'form': form,
            'tests': TESTS,
        })

    selected_keys = form.cleaned_data['selected_tests']
    feature_keys  = get_question_order(selected_keys)
    survey_form   = build_survey_form(feature_keys)

    # Build the ordered list of question metadata to drive the template
    questions_meta = _build_questions_meta(feature_keys, survey_form)

    return render(request, 'survey/survey.html', {
        'survey_form':    survey_form,
        'questions_meta': questions_meta,
        'selected_tests': selected_keys,
        'selected_tests_json': json.dumps(selected_keys),
        'tests': TESTS,
    })


@require_http_methods(['POST'])
def submit_survey(request):
    """
    Handles survey form submission.
    Validates, runs predictions, stores results in session, redirects to results.
    """
    selected_keys_raw = request.POST.get('selected_tests', '')
    try:
        selected_keys = json.loads(selected_keys_raw)
    except (ValueError, TypeError):
        return redirect('index')

    feature_keys = get_question_order(selected_keys)
    survey_form  = build_survey_form(feature_keys, data=request.POST)

    if not survey_form.is_valid():
        questions_meta = _build_questions_meta(feature_keys, survey_form)
        return render(request, 'survey/survey.html', {
            'survey_form':    survey_form,
            'questions_meta': questions_meta,
            'selected_tests': selected_keys,
            'selected_tests_json': json.dumps(selected_keys),
            'tests': TESTS,
        })

    results = run_all_predictions(selected_keys, survey_form.cleaned_data)
    answers_summary = _build_answers_summary(feature_keys, survey_form.cleaned_data)
    request.session['results'] = results
    request.session['answers_summary'] = answers_summary
    return redirect('results')


def results(request):
    """Results page."""
    results = request.session.get('results')
    if not results:
        return redirect('index')
    answers_summary = request.session.get('answers_summary', [])
    return render(request, 'survey/results.html', {
        'results': results,
        'answers_summary': answers_summary,
    })


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _build_questions_meta(feature_keys, survey_form):
    """
    Builds a list of dicts used by the template to render each question block.
    Handles the special multi-field cases (bmi_inputs, bp_inputs).
    """
    meta = []
    rendered_specials = set()

    for key in feature_keys:
        q = QUESTIONS[key]
        qtype = q['type']

        if qtype == 'bmi_inputs' and 'bmi' not in rendered_specials:
            rendered_specials.add('bmi')
            meta.append({
                'key': 'bmi',
                'type': 'bmi_inputs',
                'label': q['label'],
                'question': q['question'],
                'hint': q['hint'],
                'fields': {
                    'height_ft': survey_form['height_ft'],
                    'height_in': survey_form['height_in'],
                    'weight_lb': survey_form['weight_lb'],
                },
            })

        elif qtype in ('radio', 'binary_radio', 'season'):
            meta.append({
                'key': key,
                'type': qtype,
                'label': q['label'],
                'question': q['question'],
                'hint': q['hint'],
                'field': survey_form[key],
                'choices': q['choices'],
            })

        elif qtype == 'number':
            meta.append({
                'key': key,
                'type': 'number',
                'label': q['label'],
                'question': q['question'],
                'hint': q['hint'],
                'field': survey_form[key],
                'attrs': q.get('attrs', {}),
            })

    return meta


def _build_answers_summary(feature_keys, cleaned_data):
    """
    Builds a human-readable list of question/answer pairs for display
    on the results page. Handles BMI (computed), radio choices, and numbers.
    """
    summary = []

    for key in feature_keys:
        q = QUESTIONS[key]
        qtype = q['type']
        label = q['label']

        if qtype == 'bmi_inputs':
            ft  = int(cleaned_data.get('height_ft', 0) or 0)
            ins = int(cleaned_data.get('height_in', 0) or 0)
            lbs = float(cleaned_data.get('weight_lb', 0) or 0)
            total_in = ft * 12 + ins
            bmi = round((lbs * 703) / (total_in ** 2), 1) if total_in > 0 and lbs > 0 else '—'
            summary.append({
                'label': 'Height',
                'answer': f"{ft} ft {ins} in",
            })
            summary.append({
                'label': 'Weight',
                'answer': f"{lbs:.0f} lbs",
            })
            summary.append({
                'label': 'BMI (calculated)',
                'answer': str(bmi),
            })

        elif qtype in ('radio', 'binary_radio', 'season'):
            raw_val = cleaned_data.get(key)
            # Find the matching choice label
            answer = str(raw_val)
            for val, choice_label in q['choices']:
                if str(val) == str(raw_val):
                    answer = choice_label
                    break
            summary.append({'label': label, 'answer': answer})

        elif qtype == 'number':
            raw_val = cleaned_data.get(key)
            # Special case: sedentary time was entered as hours, display as hours
            if key == 'sedentary_time_per_day':
                summary.append({'label': label, 'answer': f"{raw_val} hours"})
            else:
                summary.append({'label': label, 'answer': str(raw_val) if raw_val is not None else '—'})

    return summary
