# -*- coding: utf-8 -*-
"""Abacus AI NLP Workshop.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eyAGA8XoyjBDQI2IanH9rO1hSV-ZMQrx
"""

!pip install -U abacusai

import collections
import threading
import time

from tqdm import tqdm
import numpy as np
import IPython.display

import abacusai

"""# Set up API client and load data"""

api_key = '9aaf73ff552c4914b6a4642f46115cdc'
server = 'https://abacus.ai'

api_client = abacusai.ApiClient(api_key=api_key, server=server)
api_client

feature_group = api_client.describe_feature_group('')
data = feature_group.load_as_pandas()
data.head()

"""# Get predictions from sentiment model"""

# Replace this code with code in predictions API screen

from abacusai import PredictionClient
client = PredictionClient()
client.get_sentiment(deployment_token='deployment token goes here', deployment_id='deployment id goes here',
                     document="I love my car, it's awesome!")

sent_deployment_token = 'deployment token goes here'
sent_deployment_id = 'deployment id goes here'

tqdm._instances.clear()
sample_texts = data['review'][:100]
sentiments = [
    client.get_sentiment(
        deployment_token=sent_deployment_token,
        deployment_id=sent_deployment_id,
        document=text
    )
    for text in tqdm(sample_texts)
]

query = 'joy'
print(f'Top scoring texts for: "{query}"\n')
scores = [s[query] for s in sentiments]
arg_sort = np.argsort(-np.array(scores))
for i in arg_sort[:5]:
    print(scores[i])
    print(sample_texts[i])
    print('')

query = 'annoyance'
print(f'Top scoring texts for: "{query}"\n')
scores = [s[query] for s in sentiments]
arg_sort = np.argsort(-np.array(scores))
for i in arg_sort[:5]:
    print(scores[i])
    print(sample_texts[i])
    print('')

query = 'fear'
print(f'Top scoring texts for: "{query}"\n')
scores = [s[query] for s in sentiments]
arg_sort = np.argsort(-np.array(scores))
for i in arg_sort[:5]:
    print(scores[i])
    print(sample_texts[i])
    print('')

"""# Create a classification model"""

print('Creating project')
class_project = api_client.create_project('nlp_classification', use_case='NLP_CLASSIFICATION')

api_client.add_feature_group_to_project(
    feature_group_id=feature_group, project_id=class_project, feature_group_type='DOCUMENTS'
)

class_project.set_feature_mapping(
    feature_group_id=feature_group,
    feature_name='review',
    feature_mapping='DOCUMENT',
)

print('Training model')
class_model = class_project.train_model(
    name='classification_model_1',
    training_config={
        'zero_shot_hypotheses': [
            'This text is about car speed / acceleration / slowness',
            'This text is about car price / cost / value for money',
            'This text is about car build quality',
            'This text is about car seats',
        ]
    }
)

class_model = class_model.wait_for_full_automl()
print('Deploying model')
class_deployment = api_client.create_deployment(model_id=class_model)
class_deployment = class_deployment.wait_for_deployment()
class_deployment_token = class_project.create_deployment_token()
class_deployment_id = class_deployment.deployment_id

print('Model deployed')

print('Testing prediction')
client.get_classification(
    deployment_token=class_deployment_token,
    deployment_id=class_deployment_id,
    document="This car is a bargain."
)

sample_texts = data['review'][:100]
text_classifications = []

text_to_prediction = {}

print('Producing predictions')

# Produce predictions in the background so we can do some analysis straight away

def process_data(texts):
    for text in texts:
        text_to_prediction[text] = client.get_classification(
            deployment_token=class_deployment_token,
            deployment_id=class_deployment_id,
            document=text,
        )
        
thread = threading.Thread(target=process_data, args=(sample_texts,))
thread.start()

while len(text_to_prediction) < 20:
    IPython.display.clear_output(wait=True)
    print(f'Predictions produced so far: {len(text_to_prediction)}')
    time.sleep(1)
print('Example prediction:')
list(text_to_prediction.values())[0]

predictions = []
for text in sample_texts:
    if text not in text_to_prediction:
        break
    else:
        predictions.append(text_to_prediction[text])
print(f'Predictions made so far: {len(predictions)}\n')
query = list(predictions[0].keys())[1]
print(f'Top scoring texts for: "{query}"\n')
scores = [s[query] for s in predictions]
arg_sort = np.argsort(-np.array(scores))
for i in arg_sort[:5]:
    print(f'Score = {scores[i]}')
    print(sample_texts[i])
    print('')

"""# Build a named entity recognition (NER) model"""

ner_project = api_client.create_project('named_entity_recognition', use_case='NAMED_ENTITY_RECOGNITION')

api_client.add_feature_group_to_project(
    feature_group_id=feature_group, project_id=ner_project, feature_group_type='DOCUMENTS'
)

ner_project.set_feature_mapping(
    feature_group_id=feature_group,
    feature_name='review',
    feature_mapping='DOCUMENT',
)

ner_model = ner_project.train_model(
    name='ner_model_1',
    training_config={'NER_MODEL_TYPE': "pretrained uncased 43 categories"}
)

ner_model.wait_for_full_automl()

ner_deployment = api_client.create_deployment(model_id=ner_model)

ner_deployment = ner_deployment.wait_for_deployment()

ner_deployment_token = ner_project.create_deployment_token()

ner_deployment_id = ner_deployment.deployment_id
ner_deployment_token = ner_deployment_token

client.get_labels(deployment_token=ner_deployment_token, deployment_id=ner_deployment_id, query_data={"content":"I love my Toyota Camry!"})

tqdm._instances.clear()
sample_texts = data['review'][:100]
annotations = [
    client.get_labels(deployment_token=ner_deployment_token, deployment_id=ner_deployment_id, query_data={'content': text})['annotations']
    for text in tqdm(sample_texts)
]

label_counts = collections.Counter([anno['displayName'] for anno_list in annotations for anno in anno_list])
label_counts.most_common(10)

product_counts = collections.Counter([anno['textExtraction']['textSegment']['phrase'].strip().lower()
                                      for anno_list in annotations for anno in anno_list if anno['displayName'] == 'product'])
product_counts.most_common(10)

"""# Combined analysis using multiple models"""

# Filter using NER

filtered_texts = [
    text
    for text, anno_list in zip(sample_texts, annotations)
    if any([anno['displayName'] == 'product' and 'avalon' in anno['textExtraction']['textSegment']['phrase'].strip().lower()
           for anno in anno_list])
]
len(filtered_texts)

# See top scores after the filter

predictions = []
for text in filtered_texts:
    if text not in text_to_prediction:
        break
    else:
        predictions.append(text_to_prediction[text])
query = list(predictions[0].keys())[1]
print(f'Top scoring texts for: "{query}"\n')
scores = [s[query] for s in predictions]
arg_sort = np.argsort(-np.array(scores))
for i in arg_sort[:5]:
    print(scores[i])
    print(filtered_texts[i])
    print('')