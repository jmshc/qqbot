#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'xiesheng'

import redis
import time
from string import Template

# key user_score_rank
user_score_rank = 'USER_SCORE_RANK'

# key 签到
G_KEY_USER_SIGN = 'KEY_USER_SIGN'

# key user_guess_rank
user_guess_rank = 'USER_GUESS_RANK'

# key user_score_temp
key_user_score_temp = 'USER_SCORE_TEMP'

# key guess_step
guess_step = 'GUESS_STEP'

pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True, db=2)
r = redis.Redis(connection_pool=pool)


def e_user_sign(p_user_name):
    """
    用户签到
    :param p_user_name:
    :return:
    """
    is_first = 0
    str_key = G_KEY_USER_SIGN + ':' + str(p_user_name)
    int_date = r.get(str_key)
    if not int_date:
        is_first = 1
        int_date = 0
    str_time = time.strftime('%Y%m%d', time.localtime())

    try:
        in_now_date = int(str_time)
        in_date_last = int(int_date)
    except ValueError:
        return -1

    if in_now_date > in_date_last:
        r.set(str_key, in_now_date)
    else:
        return -1
    return is_first


def user_guess(user_name, score, guess):
    if not is_step_correct(0):
        return -1
    try:
        m_score = int(score)
    except ValueError:
        return -2

    old_score = get_user_score(user_name)

    if old_score < m_score or m_score <= 0:
        return -1
    key = make_key_user_guess_rank(guess)
    r.zincrby(key, str(user_name), int(m_score))
    # 添加备份用户分数,产生结果的时候会用到
    r.zadd(key_user_score_temp, str(user_name), int(old_score) - int(m_score))
    mdf_user_score(user_name, m_score * -1)


def make_key_user_guess_rank(num):
    return user_guess_rank + ':' + str(num)


def set_step_next():
    step = r.get(guess_step)
    if not step:
        step = 0
    step = int(step)
    step += 1
    step %= 3
    r.set(guess_step, step)


def get_step():
    step = r.get(guess_step)
    if not step:
        step = 0
    return int(step)


def is_step_correct(step):
    if int(step) == get_step():
        return True
    else:
        return False


def mdf_user_score(user_name, score):
    """
    :param user_name: 用户名
    :param score: 分数
    :return: 改变成用分数
    """
    r.zincrby(user_score_rank, str(user_name), int(score))


def e_list_user_score_rank(p_start, p_end):
    """
    获取分数排行傍
    :param p_start:
    :param p_end:
    :return:
    """
    str_template = "{:<6}{:<10}{:<18}{}"
    str_list_rank = str_template.format('[排名]', '[用户]', '[积分]', '\n')
    str_template = "{:<2} {:<6} {:<18}{}"
    b_list_tup_user_rank = r.zrevrange(user_score_rank, p_start, p_end, withscores=True, score_cast_func=int)
    int_rank = 1
    for tup in b_list_tup_user_rank:
        name = tup[0] + (' ' * 5)
        str_list_rank += str_template.format(int_rank, name[0:5], tup[1], '\n')
        int_rank += 1
    return str_list_rank


def e_get_user_rank(p_user_name):
    """
    获取用户排名
    :param p_user_name:
    :return:
    """
    rank = r.zrevrank(user_score_rank, p_user_name)
    if (not rank) and (rank != 0):
        rank = -2
    return int(rank)


def get_user_score(user_name):
    score = r.zscore(user_score_rank, str(user_name))
    if not score:
        score = 0
    return int(score)


def get_user_guess_score(user_code, guess):
    key = make_key_user_guess_rank(guess)
    return int(r.zscore(key, str(user_code)))


if __name__ == '__main__':
    mdf_user_score('1002', 100)
    print(get_user_score('1002'))
    print(get_user_score('1003'))
    # set_step_next()
    # time.sleep(20)
    # set_step_next()
    user_guess('1002', 10, 1)
    print(make_key_user_guess_rank(1))