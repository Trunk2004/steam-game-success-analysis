########################################################################################################################
# Copyright (c) Martin Bustos @FronkonGames <fronkongames@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
########################################################################################################################
__author__ = "Martin Bustos <fronkongames@gmail.com>"
__copyright__ = "Copyright 2022, Martin Bustos"
__license__ = "MIT"
__version__ = "1.2.0"
__email__ = "fronkongames@gmail.com"

import sys
import os
import json
import argparse
import csv

def ProgressBar(count, total):
  bar_len = 50
  filled_len = int(round(bar_len * count / float(total)))

  percents = round(100.0 * count / float(total), 1)
  bar = '█' * filled_len + '░' * (bar_len - filled_len)

  sys.stdout.write(f'{bar} {percents}%\r')
  sys.stdout.flush()

def WriteString(app, key, default = ''):
  value = default
  if key in app and app[key] != None and app[key] != '':
    value = app[key]
  return CleanValue(value)

def WriteStringArray(app, key):
  if key not in app or app[key] is None:
    return ''

  if isinstance(app[key], dict):
    return CleanValue(app[key])

  values = []
  for value in app[key]:
    if value != None:
      values.append(CleanValue(value))

  return ','.join(values)

def WriteKey(app, key, default = '0'):
  return CleanValue(app[key]) if key in app else default

def CleanValue(value):
  if value is None:
    return ''

  if isinstance(value, (list, dict)):
    value = json.dumps(value, ensure_ascii=False)

  return str(value).replace('\n', ' ').replace('\r', ' ').strip()

print(f'Convert JSON to CSV {__version__} by {__author__}.')
parser = argparse.ArgumentParser(description='Convert JSON to CSV.')
parser.add_argument('-f', '--file', type=str, default='games.json', help='Dataset file name')
parser.add_argument('-o', '--outfile', type=str, default='games.csv', help='Output CSV file name')
args = parser.parse_args()

dataset = {}

filename = args.file
if os.path.exists(filename):
  print('Loading dataset.')
  with open(filename, 'r', encoding='utf-8') as fin:
    text = fin.read()
    if len(text) > 0:
      dataset = json.loads(text)

  print(f'Dataset with {len(dataset)} games loaded.')

  output_dir = os.path.dirname(args.outfile)
  if output_dir:
    os.makedirs(output_dir, exist_ok=True)

  with open(args.outfile, 'w', encoding="utf-8-sig", newline='') as fout:
    header = [
      'AppID',
      'Name',
      'Release date',
      'Estimated owners',
      'Peak CCU',
      'Required age',
      'Price',
      'Discount',
      'DLC count',
      'About the game',
      'Supported languages',
      'Full audio languages',
      'Reviews',
      'Header image',
      'Website',
      'Support url',
      'Support email',
      'Windows',
      'Mac',
      'Linux',
      'Metacritic score',
      'Metacritic url',
      'User score',
      'Positive',
      'Negative',
      'Score rank',
      'Achievements',
      'Recommendations',
      'Notes',
      'Average playtime forever',
      'Average playtime two weeks',
      'Median playtime forever',
      'Median playtime two weeks',
      'Developers',
      'Publishers',
      'Categories',
      'Genres',
      'Tags',
      'Screenshots',
      'Movies'
    ]

    writer = csv.writer(fout)
    writer.writerow(header)

    count = 0
    total = len(dataset)
    for appID in dataset:
      app = dataset[appID]

      data = [
        appID,
        WriteString(app, 'name'),
        WriteString(app, 'release_date'),
        WriteString(app, 'estimated_owners'),
        WriteKey(app, 'peak_ccu'),
        WriteKey(app, 'required_age'),
        WriteKey(app, 'price', '0.0'),
        WriteKey(app, 'discount'),
        WriteKey(app, 'dlc_count'),
        WriteString(app, 'about_the_game'),
        WriteStringArray(app, 'supported_languages'),
        WriteStringArray(app, 'full_audio_languages'),
        WriteString(app, 'reviews'),
        WriteString(app, 'header_image'),
        WriteString(app, 'website'),
        WriteString(app, 'support_url'),
        WriteString(app, 'support_email'),
        WriteKey(app, 'windows', 'False'),
        WriteKey(app, 'mac', 'False'),
        WriteKey(app, 'linux', 'False'),
        WriteKey(app, 'metacritic_score'),
        WriteString(app, 'metacritic_url'),
        WriteKey(app, 'user_score'),
        WriteKey(app, 'positive'),
        WriteKey(app, 'negative'),
        WriteString(app, 'score_rank'),
        WriteKey(app, 'achievements'),
        WriteKey(app, 'recommendations'),
        WriteString(app, 'notes'),
        WriteKey(app, 'average_playtime_forever'),
        WriteKey(app, 'average_playtime_2weeks'),
        WriteKey(app, 'median_playtime_forever'),
        WriteKey(app, 'median_playtime_2weeks'),
        WriteStringArray(app, 'developers'),
        WriteStringArray(app, 'publishers'),
        WriteStringArray(app, 'categories'),
        WriteStringArray(app, 'genres'),
        WriteStringArray(app, 'tags'),
        WriteStringArray(app, 'screenshots'),
        WriteStringArray(app, 'movies')
      ]

      writer.writerow(data)
      count += 1
      ProgressBar(count, total)
  
    print(f'\nDone. CSV saved to {args.outfile}')
else:
  print(f'Dataset file \'{args.file}\' not found.')
