# -*- coding: utf-8 -*-

# 插件加载方法： 
# 先运行 qqbot ，启动成功后，在另一个命令行窗口输入： qq plug qqbot.plugins.sample

import OpRedisTest
import GuessGuessLe
import sys
import copy
# list_member = []

# 支持的命令 '瓢虫': 2, '棒棒糖': 2, '月亮': 2, '太阳': 2, 都调用 2函数
G_DICT_CMD = {'菜单': 0, '竞猜': 1, '瓢虫': 2, '棒棒糖': 2, '月亮': 2, '太阳': 2, '查询': 3, '退出': 4, '签到': 5,
              '启动': 20, '上分': 21, '暂停': 22, '更新': 23, '重启': 24}

#  '签到': 4, '上分': 5, '下注 ': 6, '猜猜乐': 7}

# 开奖,竞猜选项
G_DICT_GUESS_OPTION = {'瓢虫': 1, '棒棒糖': 2, '月亮': 3, '太阳': 4}

G_TUP_OUTPUT_EMOTION = ('未定义', '/瓢虫', '/棒棒糖', '/月亮', '/太阳')

# 参与方 发消息的对象 {'qq', (contact,st_contact)}
G_DICT_PARA_USER = {}

# 群发
G_DICT_NAME_CONTACT = {}


def e_restart_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    重启
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    sys.exit(201)
    p_bot.SendTo(p_contact, '系统正在重启')


def e_update_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    更新
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    if len(p_list_cmd) < 2:
        return

    if p_contact.ctype != 'buddy':
        return

    if p_contact.name != '聖':
        return

    if p_list_cmd[1] == '好友':
        p_bot.Update('buddy')
        p_bot.SendTo(p_contact, '更新好友列表')
    else:
        gl = p_bot.List('group', p_list_cmd[1])
        if gl:
            g = gl[0]
            p_bot.Update(g)
        p_bot.SendTo(p_contact, '更新群列表')


def e_menu_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    菜单命令
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    p_bot.SendTo(p_contact, G_STR_MENU)


def e_get_user_score_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    查询用户积分
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    try:
        int_user_rank = int(OpRedisTest.e_get_user_rank(p_st_contact.name))
        int_score = int(OpRedisTest.get_user_score(p_st_contact.name))
    except ValueError:
        p_bot.SendTo(p_contact, p_st_contact.name + '未查到你的积分记录')
        return
    str_out_put_rank = OpRedisTest.e_list_user_score_rank(0, 9)
    str_out_put_rank += '------------------------\n'\
                        + "{:<2} {:<12} {:<18}{}".format(int_user_rank + 1, p_st_contact.name[0:5], int_score, '\n')
    p_bot.SendTo(p_contact, str_out_put_rank)


def e_bet_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    竞猜命令 只输出竞猜格式
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    p_bot.SendTo(p_contact, '--------------------\n '
                            ' 格式:[竞猜目标] [积分]\n '
                            ' 瓢虫    100   猜中赢 2  倍\n '
                            ' 棒棒糖 100   猜中赢 3  倍\n '
                            ' 月亮    100   猜中赢 6  倍\n '
                            ' 太阳    100   猜中赢 50 倍\n'
                            '--------------------\n ')


def e_user_bet_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    实际,真正的竞猜下注命令
    竞猜 格式 月亮 100
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    try:  # 参数合法性检查
        int_guess_option = int(G_DICT_GUESS_OPTION.get(p_list_cmd[0]))
        int_guess_score = int(p_list_cmd[1])
    except ValueError:
        return

    if not GuessGuessLe.G_THREAD_RUN_FLAG:
        p_bot.SendTo(p_contact, '游戏还没有开始,现在不能竞猜,请稍等')
        return -1

    if -1 == OpRedisTest.user_guess(p_st_contact.name, int_guess_score, int_guess_option):
        p_bot.SendTo(p_contact, '系统正在处理,现在不能竞猜,请稍等')
        return -1

    b_total_guess_score = OpRedisTest.get_user_guess_score(p_st_contact.name, int_guess_option)
    p_bot.SendTo(p_contact, p_st_contact.name + ',你竞猜' + G_TUP_OUTPUT_EMOTION[int_guess_option] + ' 共' +
                 str(b_total_guess_score) + '积分')
    G_DICT_PARA_USER[str(p_st_contact.name)] = (p_contact, p_st_contact)
    G_DICT_NAME_CONTACT[str(p_contact.name)] = p_contact


def e_user_out_guess_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
     退出竞猜
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    try:
        G_DICT_PARA_USER.pop(str(p_st_contact.name))
    except:
        pass
    try:
        G_DICT_NAME_CONTACT.pop(str(p_contact.name))
    except:
        pass
    p_bot.SendTo(p_contact, p_st_contact.name + ', 你暂时退出了游戏')


def e_start_guess_game_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    开户竞猜游戏
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    if p_contact.ctype != 'buddy':
        return
    if p_st_contact.name == '聖':
        if -1 == GuessGuessLe.create_thread_guess():
            p_bot.SendTo(p_contact, ''
                                    '--请先停止已有游戏--')
        else:
            p_bot.SendTo(p_contact, '-----启动竞猜游戏-----')


def e_stop_game_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    暂停游戏
    """
    if p_contact.ctype != 'buddy':
        return

    if p_st_contact.name == '聖':
        if -1 == GuessGuessLe.stop_thread():
            p_bot.SendTo(p_contact, ''
                                    '--暂时没有可暂停的游戏--')
        else:
            p_bot.SendTo(p_contact, '-----暂停游戏-----')


def e_user_sign_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    每天签到 ,新用户加 1000 积分,其它 500
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    int_rev = OpRedisTest.e_user_sign(p_st_contact.name)
    if int_rev == 0:
        OpRedisTest.mdf_user_score(p_st_contact.name, 500)
        p_bot.SendTo(p_contact, p_st_contact.name + ', 签到成功' + '获得 500 积分')
    elif int_rev == 1:
        OpRedisTest.mdf_user_score(p_st_contact.name, 1000)
        p_bot.SendTo(p_contact, p_st_contact.name + ', 欢迎第一次签到, 获得 1000 积分')
    else:
        p_bot.SendTo(p_contact, p_st_contact.name + ', 你今天好像已经签过到啦!')


def e_add_user_score_cmd(p_bot, p_contact, p_st_contact, p_list_cmd):
    """
    给用户增加/减少 积分, 一般都是加的咯
    :param p_bot:
    :param p_contact:
    :param p_st_contact:
    :param p_list_cmd:
    :return:
    """
    if p_contact.ctype != 'buddy':
        return
    if p_st_contact.name == '聖':
        try:
            int_user_name = p_list_cmd[1]
            int_score = int(p_list_cmd[2])
        except ValueError:
            return
        OpRedisTest.mdf_user_score(int_user_name, int_score)
        p_bot.SendTo(p_contact, '给用户' + str(int_user_name) + '上分:' + str(int_score))


# G_DICT_SWITCH = { 1: case1, 2: case2, 3: case3 } G_DICT_SWITCH[case](arg)
G_DICT_SWITCH = {
    0: e_menu_cmd,
    1: e_bet_cmd,
    2: e_user_bet_cmd,
    3: e_get_user_score_cmd,
    4: e_user_out_guess_cmd,
    5: e_user_sign_cmd,
    20: e_start_guess_game_cmd,
    21: e_add_user_score_cmd,
    22: e_stop_game_cmd,
    23: e_update_cmd,
    24: e_restart_cmd
    }

# 菜单
G_STR_MENU = '--------------------\n ' \
             ' [菜单]   查看菜单\n ' \
             ' [查询]   查询积分\n ' \
             ' [竞猜]   参与竞猜\n ' \
             ' [签到]   每天签到\n ' \
             ' [退出]   退出猜猜乐\n ' \
             '--------------------\n '

# 全局 g_bot
G_BOT_BOT = ''


def onQQMessage(bot, contact, member, content):
    try:
        str_content = str(content)
        list_cmd = str_content.split(' ')
        if list_cmd[0] in G_DICT_CMD:
            if contact.ctype == 'buddy':
                st_contact = contact
            else:
                st_contact = member
            G_DICT_SWITCH[G_DICT_CMD.get(list_cmd[0])](bot, contact, st_contact, list_cmd)
    except RuntimeError:
        bot.SendTo(contact, "出错啦!!!!" + RuntimeError)
        return

# end onMessage


def e_send_info_para_all(p_message):
    """m_set = set()
    for qq_num, contact in G_DICT_PARA_USER.items():
        m_set.add(contact[0])
    for m_contact in m_set:
        G_BOT_BOT.SendTo(m_contact, str(p_message))
"""
    m_message = p_message
    dict_name_contact = copy.deepcopy(G_DICT_NAME_CONTACT)
    for name, contact in dict_name_contact.items():
        G_BOT_BOT.SendTo(contact, str(m_message))


def e_send_info_para_one(p_user_name, p_message):
        b_contact = G_DICT_PARA_USER.get(str(p_user_name))
        G_BOT_BOT.SendTo(b_contact[0], b_contact[1].name + str(p_message))


def onPlug(bot):
    # 本插件被加载时被调用，提供 List/SendTo/GroupXXX/Stop/Restart 等接口，详见文档第五节
    # 提醒：如果本插件设置为启动时自动加载，则本函数将延迟到登录完成后被调用
    # bot ： QQBot 对象
    global G_BOT_BOT
    G_BOT_BOT = bot
    # DEBUG('%s.onPlug', __name__)