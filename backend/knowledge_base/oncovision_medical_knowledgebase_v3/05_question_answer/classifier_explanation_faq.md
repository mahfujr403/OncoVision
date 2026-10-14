# Classifier Explanation FAQ

## Why did the model predict lung adenocarcinoma?
The model's prediction is based on learned visual patterns in the image. RAG can explain general histologic features associated with lung adenocarcinoma, but it should not claim that every predicted image visibly contains a specific feature unless an explainability output actually identified it.

## Does high confidence mean certainty?
No. Confidence is a model output, not a pathology guarantee.

## What does agreement across models mean?
If multiple registered models independently produce the same class, agreement can be reported as a model-consensus signal. It is not equivalent to independent clinical validation.

## Can the assistant diagnose from symptoms?
No. Symptoms alone are outside the classifier's evidence boundary.

## Can the assistant explain the predicted class?
Yes, using source-backed educational knowledge.

## Can it give treatment?
It may explain treatment categories in general, but it should not prescribe or recommend individualized treatment.

## Source
- NCI Diagnosis: https://www.cancer.gov/about-cancer/diagnosis-staging/diagnosis
- NCI Treatment Types: https://www.cancer.gov/about-cancer/treatment/types
