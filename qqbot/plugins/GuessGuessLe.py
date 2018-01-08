#!/usr/bin/env python
# -*- coding:utf-8 -*-
__author__ = 'xiesheng'
import random
import threading
import time
import redis
import myplug
import OpRedisTest


pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True, db=2)
r = redis.Redis(connection_pool=pool)

# 抽奖流程 0 :竞猜 1: 竞猜完成,生成竞猜结束 2:竞猜成功处理
step = 0

# 总库存, 初始 10000 本
llTotal = 10000

# 这一轮回报
llThisBack = 0

# 赔数 2, 3, 6, 50 最大公约数 300 ;
maxNum = 300

# 随机数 开始和结束
start_num = 1
end_num = 306  # 300/2 + 300/3 + 300/6 + 300/50 = 306

# 赔率
arrayPayNum = [2, 3, 6, 50]

# 用户积分
user_score = {}

# 用户猜猜下注
user_guess_score = {'1': {}, '2': {}, '3': {}, '4': {}}

# key guess_step
guess_step = 'GUESS_STEP'

# key open_result
key_open_result = 'OPEN_RESULT'

# key user_guess_rank
user_guess_rank = 'USER_GUESS_RANK'

# key user_score_rank
user_score_rank = 'USER_SCORE_RANK'

# 开奖期数
G_INT_OPEN_PERIOD = 1000

# 用户分数范围控制
G_USER_SCORE_MIN = 200
G_USER_SCORE_MAX = 90000

# 开奖历史
G_LIST_OPEN_RESULT_INFO = [
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n',
    '**** *** ****** ********\n'
]

# 上期统计
G_LIST_OPEN_RECODE = [{1: 0, 2: 0, 3: 0, 4: 0}, {1: 0, 2: 0, 3: 0, 4: 0}]

#  期数
G_INT_OPEN_COUNT = 0

# 开奖输出符号
G_TUP_OUTPUT_EMOTION = ('/红包', '/瓢虫', '/棒棒糖', '/月亮', '/太阳')

# 输入 串
G_STR_OUTPUT = '{:<2}|{:<4}|{:<4}|{:<4}|{:<4}{}'.format(G_TUP_OUTPUT_EMOTION[0], G_TUP_OUTPUT_EMOTION[1],
                                                        G_TUP_OUTPUT_EMOTION[2], G_TUP_OUTPUT_EMOTION[3],
                                                        G_TUP_OUTPUT_EMOTION[4], '\n') + '-------------------\n'

# 开奖结果输出 串
G_STR_OPEN_RESULT_OUT = ''

# 线程 handle
g_thread_open_guess_deal = ''

# 线程运行标识
G_THREAD_RUN_FLAG = False

G_THREAD_RUN_FLAG_TWO = False


def make_key_user_guess_rank(num):
    return user_guess_rank + ':' + str(num)


def set_step_next():
    m_step = r.get(guess_step)
    if not m_step:
        m_step = 0
    m_step = int(m_step)
    m_step += 1
    m_step %= 3
    r.set(guess_step, m_step)


def get_step():
    m_step = r.get(guess_step)
    if not m_step:
        m_step = 0
    return int(m_step)


def go_step_next():
    """
    下一个步骤
    :return:
    """
    global step
    step += 1
    step %= 3


def delete_user_score_temp():
    r.delete(OpRedisTest.key_user_score_temp)


def delete_user_guess():
    for keys in r.keys(user_guess_rank + ':' + '?'):
        r.delete(keys)


def sett_after_open_result(result):
    """
    :rtype : object
    """
    key = make_key_user_guess_rank(result)
    int_pay_num = arrayPayNum[int(result) - 1]
    int_total_people = 0
    int_total_score = 0
    b_flag = True
    for value, score in r.zrevrange(key, 0, -1, withscores=True):
        int_score = int(score)
        get_score = int_score * int_pay_num
        update_user_score(value, get_score)
        now_score = OpRedisTest.get_user_score(str(value))
        b_contact = myplug.G_DICT_PARA_USER.get(str(value))
        if not b_contact:
            continue
        if b_contact[0].ctype == 'buddy':
            myplug.e_send_info_para_one(value, '恭喜你竞猜正确,获得 ' + str(get_score) + '积分' +
                                               '你现在共有积分 ' + str(now_score) + '积分')
        int_total_people += 1
        int_total_score += get_score

        if b_flag:
            myplug.e_send_info_para_all('恭喜 [{}] 获得本轮最高积分 {}积分'.format(b_contact[1].name, str(get_score)))
            b_flag = False

    global G_INT_OPEN_PERIOD
    G_INT_OPEN_PERIOD += 1   # 期数
    #                期数  开奖码 中奖人数 共赢得积分
    b_str_output = "{:<2} {:<2} {:<3} {:<11}{}".format(str(G_INT_OPEN_PERIOD),
                                                       G_TUP_OUTPUT_EMOTION[int(result)],
                                                       int_total_people,
                                                       int_total_score,
                                                       '\n')
    G_LIST_OPEN_RESULT_INFO.append(b_str_output)
    del G_LIST_OPEN_RESULT_INFO[0]
    delete_user_guess()
    delete_user_score_temp()


def update_user_score(user_name, score):
    """
    :param user_name: 用户名
    :param score: 分数
    :return: 改变成用分数
    """
    r.zincrby(user_score_rank, str(user_name), int(score))


def do_after_open_result(result):
    """
    开奖结果处理
    :param result:
    :return:
    """
    for key, val in user_guess_score[str(result)].items():
        int_val = int(val)
        mdf_user_score(key, int_val * arrayPayNum[int(result)])
    user_guess_score.clear()


def thread_open_guess_main():
    global G_THREAD_RUN_FLAG
    global G_INT_OPEN_COUNT
    global G_STR_OUTPUT
    global G_STR_OPEN_RESULT_OUT
    global G_THREAD_RUN_FLAG_TWO
    G_THREAD_RUN_FLAG = True
    G_THREAD_RUN_FLAG_TWO = False
    r.set(guess_step, int(0))
    # delete_user_guess()
    while G_THREAD_RUN_FLAG:
        m_step = get_step()
        if m_step == 0:
            G_INT_OPEN_COUNT += 1
            # print('距离开奖还有60s,请竞猜')
            # print('下一轮竞猜开始')
            myplug.e_send_info_para_all('---下一轮竞猜开始,请!---')
            time.sleep(30)
            myplug.e_send_info_para_all('距离开奖还有30s,请竞猜')
            time.sleep(30)
            set_step_next()
            # print('正在产生竞猜结果')
            # myplug.e_send_info_para_all('-----即将开奖-----')
        elif m_step == 1:
            do_step_one()

        elif m_step == 2:
            # 结算
            if G_THREAD_RUN_FLAG_TWO:
                G_THREAD_RUN_FLAG = False
            time.sleep(1)  # ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10
            set_step_next()


def do_step_one():
    global G_INT_OPEN_COUNT
    global G_STR_OUTPUT
    global G_STR_OPEN_RESULT_OUT
    open_result = open_guess_result()
    e_record_open(open_result)
    # time.sleep(5)
    """ myplug.e_send_info_para_all('******开奖结果为' + G_TUP_OUTPUT_EMOTION(int(open_result)) + '*****')"""
    sett_after_open_result(open_result)
    str_output_open_info = "{:<2}{:<2}{:<3}{:<11}{}".format('期数|', '开奖码|', '中奖数|', '赢积分', '\n')
    for str_list in G_LIST_OPEN_RESULT_INFO[:9]:
        str_output_open_info += str_list
    str_output_open_info += '-------------------\n'
    str_output_open_info += str(G_LIST_OPEN_RESULT_INFO[9])
    str_out = '{:<2}|{:<4}|{:<4}|{:<4}|{:<4}{}'.format('上期', G_LIST_OPEN_RECODE[0][1], G_LIST_OPEN_RECODE[0][2],
                                                       G_LIST_OPEN_RECODE[0][3], G_LIST_OPEN_RECODE[0][4], '\n')
    str_out += '{:<2}|{:<4}|{:<4}|{:<4}|{:<4}{}'.format('本期', G_LIST_OPEN_RECODE[1][1], G_LIST_OPEN_RECODE[1][2],
                                                        G_LIST_OPEN_RECODE[1][3], G_LIST_OPEN_RECODE[1][4], '\n')
    str_out += '-------------------\n'
    G_STR_OPEN_RESULT_OUT += G_TUP_OUTPUT_EMOTION[int(open_result)]
    if 0 == (G_INT_OPEN_COUNT % 6):
        G_STR_OPEN_RESULT_OUT += '\n'
    # myplug.e_send_info_para_all(str_output_open_info)
    str_put = G_STR_OUTPUT + str_out + G_STR_OPEN_RESULT_OUT
    myplug.e_send_info_para_all(str_put)
    if 0 == (G_INT_OPEN_COUNT % 42):
        time.sleep(10)
        G_STR_OPEN_RESULT_OUT = ''
        G_INT_OPEN_COUNT = 0
        G_LIST_OPEN_RECODE.pop(0)
        G_LIST_OPEN_RECODE.append({1: 0, 2: 0, 3: 0, 4: 0})
    # print('开奖结果为 %d' % open_result)
    set_step_next()


def e_record_open(p_open_result):
    """
    记录上期开奖和本期的
    :param p_open_result:
    :return:
    """
    G_LIST_OPEN_RECODE[1][p_open_result] += 1


def user_guess(user_name, score, guess):
    str_user_name = str(user_name)
    int_score = int(score)
    str_guess = str(guess)

    old_score = user_score.get(str_user_name, 0)
    if old_score - int_score < 0:
        return -1
    add_two_dim_dict(str_guess, str_user_name, int_score)
    mdf_user_score(str_user_name, -int_score)
    return 0


def add_two_dim_dict(key_a, key_b, val):
    """
    竞猜队列
    :param key_a:猜的数
    :param key_b: 用户代码
    :param val: 竞猜数量
    :return:
    """
    if key_a in user_guess_score:
        user_guess_score[key_a].update({key_b: val})
    else:
        user_guess_score.update({key_a: {key_b: val}})


def set_open_result(num):
    r.set(key_open_result, num)


def get_open_result():
    result = r.get(key_open_result)
    if not result:
        return -1
    return int(result)


def check_before_open():
    """
    开奖前检查
    :return:
    """
    dict_result_love = {1: 500, 2: 500, 3: 500, 4: 500}
    dict_user_score = {}
    list_result = []
    list_tup_user_score_temp = r.zrevrange(OpRedisTest.key_user_score_temp, 0, -1, withscores=True)
    for tup_user_score in list_tup_user_score_temp:
        dict_user_score[tup_user_score[0]] = tup_user_score[1]

    for result in (1, 2, 3, 4):
        key = make_key_user_guess_rank(result)
        for user_name, score in r.zrevrange(key, 0, -1, withscores=True):
            int_user_score = dict_user_score[user_name]
            int_pay_num = score * arrayPayNum[int(result) - 1]

            if int_user_score < G_USER_SCORE_MIN:
                dict_result_love[int(result)] -= 1
            if int_user_score + int_pay_num >= G_USER_SCORE_MAX:
                dict_result_love[int(result)] += 1 * 1000
    tup_min_result = min(dict_result_love.items(), key=lambda x: x[1])
    # tup_max_result = max(dict_result_love.items(), key=lambda x: x[1])

    for result, num in dict_result_love.items():
            if num == tup_min_result[1]:
                list_result.append(int(result))
    return list_result


def open_guess_result():
    """
    产生猜猜乐结果, 和等级范围就是 300/2, 3, 6, 50 的结果范围
    :return:
    """
    int_try_count = 50
    list_result_want = check_before_open()
    while int_try_count > 0:
        result = random.randint(start_num, end_num)
        if (result >= 1) and (result <= 150):
            open_result = 1
        elif (result > 150) and (result <= 250):
            open_result = 2
        elif (result > 250) and (result <= 300):
            open_result = 3
        elif (result > 300) and (result <= 306):
            open_result = 4
        else:
            open_result = 1

        if open_result in list_result_want:
            break
        int_try_count -= 1

    set_open_result(open_result)
    print('666666  ' + str(list_result_want) + str(open_result))
    return open_result


def mdf_user_score(user_name, score):
    """
    :param user_name: 用户名
    :param score: 分数
    :return: 改变成用分数
    """
    old_score = user_score.get(user_name, 0)
    now_score = old_score + int(score)
    user_score[str(user_name)] = now_score
    return now_score


def print_user_score_all():
    """
    输出全部用户的分数
    :return:
    """
    print(user_score)


def clear_dict(this_dict):
    """
    清除字典
    :param this_dict:
    :return:
    """
    this_dict.clear()


def stop_thread():
    global G_THREAD_RUN_FLAG
    global G_THREAD_RUN_FLAG_TWO
    if G_THREAD_RUN_FLAG:
        G_THREAD_RUN_FLAG_TWO = True
    else:
        return -1


def create_thread_guess():
    global g_thread_open_guess_deal
    if G_THREAD_RUN_FLAG:
        return -1
    g_thread_open_guess_deal = threading.Thread(target=thread_open_guess_main)
    # thread_open_guess_deal.setDaemon(True)
    g_thread_open_guess_deal.start()


def bot_to_guess():
    mdf_user_score('10001', 10)
    time.sleep(10)

if __name__ == '__main__':

    create_thread_guess()

    while True:
        op = input('请输入操作数:')
        if op == 'a':
            m_user_code, m_score = (str(x) for x in input('请输入用户代码和分数:').split(' '))
            print(m_user_code, ' ', m_score)
            mdf_user_score(m_user_code, m_score)
            print_user_score_all()
        elif op == 'b':
            m_user_code, m_score, m_guess = (str(x) for x in input('请输入用户代码,分数和猜的数:').split(' '))
            user_guess(m_user_code, m_score, m_guess)
            print(user_guess_score)
        elif op == 'c':
            print("你确定要清除字典? Y/N")
            op = input()
            if op == 'Y' or op == 'y':
                clear_dict(user_guess_score)
                print(user_guess_score)
