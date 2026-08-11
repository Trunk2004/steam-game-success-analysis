import argparse
import csv
import json
import os
from datetime import datetime


DEFAULT_INFILE = os.path.join('output', 'game_data.json')
DEFAULT_STATS_OUTFILE = os.path.join('output', 'game_stats.csv')
DEFAULT_HISTORY_OUTFILE = os.path.join('output', 'game_history_by_month.csv')


def clean_number(value):
    if value is None:
        return ''
    return str(value).replace(',', '').strip()


def load_dataset(filename):
    with open(filename, 'r', encoding='utf-8') as fin:
        data = json.load(fin)

    if isinstance(data, dict):
        return data

    if isinstance(data, list):
        return {str(item.get('appid', index)): item for index, item in enumerate(data)}

    raise ValueError('Input JSON must be an object or a list.')


def appid_sort_key(appid):
    appid_text = str(appid)
    return (0, int(appid_text)) if appid_text.isdigit() else (1, appid_text)


def month_sort_key(month):
    if month == 'Last 30 Days':
        return (1, datetime.max)

    try:
        return (0, datetime.strptime(month, '%B %Y'))
    except ValueError:
        return (2, month)


def write_stats_csv(dataset, filename):
    fieldnames = [
        'appid',
        'current_players',
        'peak_players_24h',
        'peak_players_all_time',
        'error_code',
        'error_message',
    ]

    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filename, 'w', encoding='utf-8-sig', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for appid in sorted(dataset.keys(), key=appid_sort_key):
            game = dataset[appid] or {}
            stats = game.get('game_stats') or {}
            error = stats.get('error') if isinstance(stats.get('error'), dict) else {}

            writer.writerow({
                'appid': game.get('appid', appid),
                'current_players': clean_number(stats.get('Current Players')),
                'peak_players_24h': clean_number(stats.get('Peak Players 24h')),
                'peak_players_all_time': clean_number(stats.get('Peak Players All Time')),
                'error_code': error.get('code', ''),
                'error_message': error.get('message', ''),
            })

    return len(dataset)


def write_history_csv(dataset, filename):
    appids = sorted(dataset.keys(), key=appid_sort_key)
    months = set()
    player_by_month = {}

    for appid in appids:
        game = dataset[appid] or {}
        for month_data in game.get('game_history') or []:
            month = month_data.get('Month', '')
            if not month:
                continue

            months.add(month)
            player_by_month.setdefault(month, {})[appid] = clean_number(month_data.get('Avg Players'))

    sorted_months = sorted(months, key=month_sort_key)
    fieldnames = ['month'] + appids

    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filename, 'w', encoding='utf-8-sig', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for month in sorted_months:
            row = {'month': month}
            for appid in appids:
                row[appid] = player_by_month.get(month, {}).get(appid, '')
            writer.writerow(row)

    return len(sorted_months), len(appids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert historical SteamCharts JSON to analysis-friendly CSV files.')
    parser.add_argument('-f', '--file', type=str, default=DEFAULT_INFILE,
                        help='Input historical JSON file')
    parser.add_argument('--stats-outfile', type=str, default=DEFAULT_STATS_OUTFILE,
                        help='Output CSV for current/peak game stats')
    parser.add_argument('--history-outfile', type=str, default=DEFAULT_HISTORY_OUTFILE,
                        help='Output CSV for monthly average players, with app IDs as columns')
    args = parser.parse_args()

    dataset = load_dataset(args.file)
    stats_count = write_stats_csv(dataset, args.stats_outfile)
    month_count, app_count = write_history_csv(dataset, args.history_outfile)

    print(f'Wrote {stats_count} games to {args.stats_outfile}')
    print(f'Wrote {month_count} months x {app_count} games to {args.history_outfile}')
