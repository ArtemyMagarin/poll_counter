#!/usr/bin/env python3

import re
import sys
from pprint import pprint
from datetime import datetime
import time
import requests
import config


TOKEN = config.token


def make_api_request(method, params):
    params['access_token'] = TOKEN
    params['v'] = 5.92
    time.sleep(0.34)
    r = requests.get('https://api.vk.com/method/{0}'.format(method), params=params).json()
    if 'error' in r:
        print('Error:', method, params, r)
        return r
    else:
        return r['response']


def parse_poll_data(url):
    owner_id, poll_id = url.split("?")[1].replace('w=poll', '').split('_')
    return (owner_id, poll_id)


def fetch_poll_data(poll_id, owner_id):
    params = {
        'poll_id':  poll_id,
        'owner_id': owner_id}

    data = make_api_request('polls.getById', params)
    return data


def fetch_poll_stats(poll_id, owner_id, answer_ids):
    params = {
        'poll_id':  poll_id,
        'owner_id': owner_id,
        'answer_ids': answer_ids if type(answer_ids) in [str, int] else ','.join([str(i) for i in answer_ids])}

    data = make_api_request('polls.getVoters', params)
    return data


def get_polls_data():
    args = sys.argv[1:]
    input_file = list(filter(lambda item: '-i=' in item, args))
    polls_data = []

    if not len(input_file):
        print('Usage: %s -i=filename.txt' % sys.argv[0])
    else:
        input_filename = input_file[0].replace('-i=', '')
        with open(input_filename, 'r') as f:
            polls_data = f.read().strip().split('\n')

    return list(map(lambda item: tuple(item.split(';')), polls_data))


def get_right_voters_ids(url, answer):
    owner_id, poll_id = parse_poll_data(url)
    poll_obj = fetch_poll_data(poll_id, owner_id)
    answer_id = list(filter(lambda item: item['text'].strip() == answer.strip(), poll_obj['answers']))[0]['id']
    stats = fetch_poll_stats(poll_id, owner_id, answer_id)
    return stats[0]['users']['items']


def get_users_info(ids, fields='id,first_name,last_name,nickname,domain'):
    params = {
        'user_ids': ','.join([str(id) for id in ids]),
        'fields': fields
    }
    return make_api_request('users.get', params)


def make_stats_report(vote_data, users):
    res = []
    for user in users:
        first_name = user['first_name']
        last_name = user['last_name']
        domain = user['domain'] if user['domain'] else 'id{id}'.format(id=user['id'])
        votes = vote_data[user['id']]
        link = 'https://vk.com/{domain}'.format(domain=domain)

        s = '{votes} - {first_name} {last_name}{space}({link})'.format(
            votes=(votes if votes > 9 else ' {}'.format(votes)),
            first_name=first_name,
            last_name=last_name,
            link=link,
            space=' '*(30-len(first_name+last_name+' ')))  # len('Константин Константинопольский') == 30

        res.append((int(votes), s))

    res.sort(key=lambda item: item[0], reverse=True)
    res = list(map(lambda item: item[1], res))

    report = '\n'.join(res) + '\n\nCreated date: {}\n'.format(datetime.now().strftime('%c'))
    return report


def main():
    voters = {}
    print('\nProcessing...')

    polls_data = get_polls_data()
    if not len(polls_data):
        return 1

    for i, data in enumerate(polls_data):
        url, answer = data
        right_voters = get_right_voters_ids(url, answer)

        print(i+1, url, "right answers:", len(right_voters))

        for voter in right_voters:
            if voter in voters:
                voters[voter] += 1
            else:
                voters[voter] = 1

    users = get_users_info(voters.keys())
    report = make_stats_report(voters, users)

    with open('report.txt', 'w') as f:
        f.write(report)

    print("Report:")
    print(report)


def test():
    polls_data = get_polls_data()
    if not len(polls_data):
        return 1

    print("Testing:\n")

    failed = passed = 0
    for i, data in enumerate(polls_data):
        url, answer = data
        owner_id, poll_id = parse_poll_data(url)

        poll_obj = fetch_poll_data(poll_id, owner_id)
        answers = list(map(lambda item: item['text'].strip(), poll_obj['answers']))
        if not answer.strip() in answers:
            print(i+1, 'Error: answer:', answer.strip(), 'expected:', ' or '.join(answers))
            failed += 1
        else:
            print(i+1, 'OK')
            passed += 1

    print("Result: failed {0}, passed {1}".format(failed, passed))


if __name__ == '__main__':
    if not TOKEN:
        raise Exception("Token must be setted")

    if '--skip-tests' not in sys.argv:
        test()
    else:
        print("Tests were been skipped")

    if '--test' not in sys.argv:
        main()
    else:
        print('Tests only')
