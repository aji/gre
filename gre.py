#!/usr/bin/python
# gre.py -- Alex's g/re/ script

import re
import weechat


def lineextract(lines):
    tags = weechat.infolist_string(lines, 'tags').split(',')

    kind = tags[0]

    nick = ''
    for tag in tags:
        key, _, val = tag.partition('_')
        if key == 'nick':
            nick = val

    text = weechat.infolist_string(lines, 'message')

    return kind, nick, text

# yields tuples: chan, nick, text
def privmsgs(ptr):
    lines = weechat.infolist_get('buffer_lines', ptr, '')

    chan = weechat.buffer_get_string(ptr, 'localvar_channel')

    while weechat.infolist_prev(lines):
        kind, nick, text = lineextract(lines)

        if kind == 'irc_privmsg':
            yield chan, nick, text

    weechat.infolist_free(lines)


def iter_global(refbuf):
    bufs = weechat.infolist_get('buffer', '', '')

    while weechat.infolist_next(bufs):
        ptr = weechat.infolist_get_pointer(bufs, 'pointer')
        kind = weechat.buffer_get_string(ptr, 'localvar_type')

        if kind == 'channel':
            yield ptr

    weechat.infolist_free(bufs)

def iter_server(refbuf):
    bufs = weechat.infolist_get('buffer', '', '')
    refserv = weechat.buffer_get_string(refbuf, 'localvar_server')

    while weechat.infolist_next(bufs):
        ptr = weechat.infolist_pointer(bufs, 'pointer')
        kind = weechat.buffer_get_string(ptr, 'localvar_type')
        serv = weechat.buffer_get_string(ptr, 'localvar_server')

        if kind == 'channel' and refserv == serv:
            yield ptr

    weechat.infolist_free(bufs)

def iter_channel(refbuf):
    kind = weechat.buffer_get_string(refbuf, 'localvar_type')

    if kind == 'channel':
        yield refbuf


def mark_null(chan, nick, p):
    return None
def dupe_null(chan, nick, p):
    return False

def mark_channel(chan, nick, p):
    p = [] if p == None else p
    p.append(chan)
    return p
def dupe_channel(chan, nick, p):
    return p != None and chan in p

def mark_nick(chan, nick, p):
    p = [] if p == None else p
    p.append(nick)
    return p
def dupe_nick(chan, nick, p):
    return p != None and nick in p

def mark_channick(chan, nick, p):
    p = {} if p == None else p
    if not chan in p:
        p[chan] = []
    p[chan].append(nick)
    return p
def dupe_channick(chan, nick, p):
    if p == None or not chan in p:
        return False
    return nick in p[chan]


def gre_get_opts(args):
    s = []

    args = args.lstrip()
    while args[0] == '-':
        opt, _, args = args.partition(' ')

        s.append(opt)
        args = args.lstrip()

    return s, args

def gre_get_regex(args):
    args = args.lstrip()

    if args[0] != '/':
        return '', args

    args = args[1:]
    s, _, args = args.partition('/')

    return re.compile(s), args.lstrip()


def gre_command(data, cur_buf, args):
    opts, rest = gre_get_opts(args)
    text_re, rest = gre_get_regex(rest)

    iterfunc = iter_channel

    markfunc = mark_nick
    dupefunc = dupe_nick

    excl_me = True

    action = weechat.command

    limit = -1

    for opt in opts:
        if opt == '-global':
            iterfunc = iter_global
        if opt == '-server':
            iterfunc = iter_server
        if opt == '-channel':
            iterfunc = iter_channel

        if opt == '-try':
            action = weechat.prnt

        if opt == '-me':
            excl_me = False

        if opt == '-c':
            markfunc = mark_channel
            dupefunc = dupe_channel
        if opt == '-n':
            markfunc = mark_nick
            dupefunc = dupe_nick
        if opt == '-cn':
            markfunc = mark_channick
            dupefunc = dupe_channick

        if opt[1:].isdigit():
            limit = int(opt[1:])

    p = None

    for buf in iterfunc(cur_buf):
        nick_me = weechat.buffer_get_string(buf, 'localvar_nick')

        count = 0
        for chan, nick, text in privmsgs(buf):
            m = text_re.search(text)

            if excl_me and nick == nick_me:
                continue

            if count == limit:
                continue
            count += 1

            if m and not dupefunc(chan, nick, p):
                p = markfunc(chan, nick, p)

                command = rest.replace('$c', chan).replace('$n', nick).replace('$0', text)
                lastindex = 0 if m.lastindex == None else 9 if m.lastindex > 9 else m.lastindex
                for matchidx in range(1, lastindex + 1):
                    command = command.replace('${}'.format(matchidx), m.group(matchidx))

                action(buf, command)

    return weechat.WEECHAT_RC_OK

def gre_init():
    weechat.register('gre', 'Alex Iadicicco', '0.1', 'GPL3', 'g/re/ functionality for WeeChat', '', '')
    weechat.hook_command('gre', 'g/re/', '[-server|-global] [-c|-n|-cn] [-###] /text/ action', '', '', 'gre_command', '')

gre_init()
