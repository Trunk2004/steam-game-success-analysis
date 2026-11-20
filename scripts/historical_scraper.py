# Source - https://stackoverflow.com/a/78250723
# Posted by Serpensin
# Retrieved 2026-07-02, License - CC BY-SA 4.0

import argparse
import asyncio
import json
import os
import shutil
import sys
import time

import aiohttp
import http
from bs4 import BeautifulSoup


DEFAULT_AUTOSAVE = 100
DEFAULT_OUTFILE = 'game_data.json'
DEFAULT_RETRIES = 4
DEFAULT_SLEEP = 1.5
DEFAULT_TIMEOUT = 20
NO_RETRY_STATUSES = {404, 500}
RETRY_STATUSES = {429, 502, 503, 504}


def SaveJSON(data, filename):
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as fout:
        json.dump(data, fout, indent=2, ensure_ascii=False)


def LoadJSON(filename):
    if not os.path.exists(filename):
        return {}

    with open(filename, 'r', encoding='utf-8') as fin:
        content = fin.read().strip()

    if not content:
        return {}

    data = json.loads(content)
    return data if isinstance(data, dict) else {}


def ProgressBar(title, count, total):
    '''
    Displays and updates a progress bar.
    '''
    if total == 0:
        return

    terminal_width = shutil.get_terminal_size((100, 20)).columns
    prefix = f"[i {time.strftime('%H:%M:%S')}] {title} "
    suffix = f" {round(100.0 * count / float(total), 2)}% ({count}/{total})"
    bar_len = max(10, min(40, terminal_width - len(prefix) - len(suffix) - 2))
    filled_len = int(round(bar_len * count / float(total)))

    bar = '#' * filled_len + '-' * (bar_len - filled_len)
    line = f'{prefix}{bar}{suffix}'

    sys.stdout.write('\r' + line.ljust(terminal_width - 1)[:terminal_width - 1])
    sys.stdout.flush()


async def playercount(session, gameid, retries=DEFAULT_RETRIES, sleep=DEFAULT_SLEEP):
    url = f'https://steamcharts.com/app/{gameid}'

    for attempt in range(retries + 1):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    break

                if response.status in RETRY_STATUSES and attempt < retries:
                    retry_after = response.headers.get('Retry-After')
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else min(sleep * (2 ** attempt), 60)
                    await asyncio.sleep(wait)
                    continue

                message = http.HTTPStatus(response.status).phrase
                if response.status in NO_RETRY_STATUSES:
                    message = f'{message} (SteamCharts has no data for this app)'

                return {
                    'appid': gameid,
                    'error': {
                        'code': response.status,
                        'message': message
                    }
                }
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            if attempt < retries:
                wait = min(sleep * (2 ** attempt), 60)
                await asyncio.sleep(wait)
                continue

            return {
                'appid': gameid,
                'error': {
                    'code': 'request_failed',
                    'message': str(ex)
                }
            }
    else:
        return {
            'appid': gameid,
            'error': {
                'code': 'request_failed',
                'message': 'No response body returned'
            }
        }

    soup = BeautifulSoup(html, 'html.parser')
    data = {'appid': gameid}
    count = 0

    for stats in soup.find_all('div', class_='app-stat'):
        for stat in stats.find_all('span', class_='num'):
            value = stat.text.strip()
            if count == 0:
                data['Current Players'] = value
            elif count == 1:
                data['Peak Players 24h'] = value
            elif count == 2:
                data['Peak Players All Time'] = value
            count += 1

    history_data = []
    history_table = soup.find('table', class_='common-table')
    history_body = history_table.find('tbody') if history_table else None
    if history_body:
        for row in history_body.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 5:
                month = cols[0].text.strip()
                players = cols[1].text.strip()
                peak = cols[4].text.strip()
                history_data.append({
                    'Month': month,
                    'Avg Players': players,
                    'Peak Players': peak
                })

    data['History'] = history_data
    return data


def split_game_data(game_data):
    game_id = game_data.get('appid', 'unknown')
    game_stats = {k: v for k, v in game_data.items() if k not in ('History', 'appid')}
    game_history = game_data.get('History', [])
    return game_id, game_stats, game_history


def format_game_data(game_data):
    game_id, game_stats, game_history = split_game_data(game_data)
    return game_id, {
        'appid': game_id,
        'game_stats': game_stats,
        'game_history': game_history
    }


async def scrape_games(game_ids, output_file, concurrency=4, autosave=DEFAULT_AUTOSAVE,
                       retries=DEFAULT_RETRIES, sleep=DEFAULT_SLEEP):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36'
    }
    timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
    dataset = LoadJSON(output_file)
    game_ids = [str(gameid).strip() for gameid in game_ids if str(gameid).strip()]
    game_ids = [gameid for gameid in game_ids if gameid not in dataset]
    total = len(game_ids)
    completed = 0
    completed_since_save = 0

    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async def fetch(gameid):
                result = await playercount(session, gameid, retries=retries, sleep=sleep)
                await asyncio.sleep(sleep)
                return result

            queue = asyncio.Queue()
            for gameid in game_ids:
                queue.put_nowait(gameid)

            async def worker():
                nonlocal completed, completed_since_save

                while True:
                    try:
                        gameid = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    try:
                        result = await fetch(gameid)
                        game_id, combined_data = format_game_data(result)
                        dataset[str(game_id)] = combined_data
                        completed_since_save += 1

                        if autosave > 0 and completed_since_save >= autosave:
                            SaveJSON(dataset, output_file)
                            completed_since_save = 0
                    except asyncio.CancelledError:
                        raise
                    except Exception as ex:
                        print(f'\nError scraping {gameid}: {ex}')
                    finally:
                        completed += 1
                        ProgressBar('Scraping history', completed, total)
                        queue.task_done()

            workers = [asyncio.create_task(worker()) for _ in range(min(concurrency, total))]
            await asyncio.gather(*workers)
    finally:
        SaveJSON(dataset, output_file)

    ProgressBar('Scraping history', total, total)
    print()  # newline after progress output
    return dataset


def parse_appids(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def load_appids_from_file(path):
    with open(path, 'r', encoding='utf-8') as fin:
        content = fin.read().strip()

    if not content:
        return []

    if path.lower().endswith('.json'):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            pass

    appids = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            appids.append(line)
    return appids


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape SteamCharts stats and history for multiple games')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--appids', type=parse_appids,
                       help='Comma-separated list of Steam app IDs, e.g. 1446780,570')
    group.add_argument('--input-file', type=str,
                       help='Text file with one Steam app ID per line')
    parser.add_argument('-o', '--output-file', type=str, default=os.path.join('output', DEFAULT_OUTFILE),
                        help='JSON file where all scraped games will be written')
    parser.add_argument('-c', '--concurrency', type=int, default=4,
                        help='Maximum number of concurrent requests')
    parser.add_argument('-a', '--autosave', type=int, default=DEFAULT_AUTOSAVE,
                        help='Save the combined output every N completed games (0 only saves at the end)')
    parser.add_argument('-r', '--retries', type=int, default=DEFAULT_RETRIES,
                        help='Number of retries for temporary request failures')
    parser.add_argument('-s', '--sleep', type=float, default=DEFAULT_SLEEP,
                        help='Delay after each request')
    args = parser.parse_args()

    if args.appids:
        app_ids = args.appids
    else:
        app_ids = load_appids_from_file(args.input_file)

    print(f'Scraping {len(app_ids)} games to "{args.output_file}"...')
    print(f'Autosaving combined output every {args.autosave} completed games.')
    try:
        asyncio.run(scrape_games(app_ids, output_file=args.output_file,
                                 concurrency=args.concurrency,
                                 autosave=args.autosave,
                                 retries=args.retries,
                                 sleep=args.sleep))
    except KeyboardInterrupt:
        print(f'\nInterrupted. Progress saved to "{args.output_file}".')

#python historical_scraper.py --input-file applist.json -o output/game_data.json --concurrency 4
