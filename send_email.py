# -*- coding: utf-8 -*-
import smtplib
import traceback
from email.mime.text import MIMEText


def send_email(to_addrs, subject, plainText):
    msg = MIMEText(plainText,'html', 'utf-8')
    from_addr = 'noreply@chinacache.com'
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ','.join(to_addrs)
    #s = smtplib.SMTP('corp.chinacache.com')
    s = smtplib.SMTP('anonymousrelay.chinacache.com')
    try:
        s.ehlo()
        s.starttls()
        s.ehlo()
    except:
        logger.debug("%s STARTTLS extension not supported by server" % msg['To'])
        pass
    #s.login('noreply', 'SnP123!@#')
    s.sendmail(from_addr, to_addrs, msg.as_string())
    s.quit()


def send_email_for_start(to_addrs, task, error_info):
    '''
    任务启动邮件发送
    '''
    username = task['username']
    start_datetime = task['start_datetime']
    task_id = task['_id']

    body = u'Hi,预计在%s执行的%s任务,'%(start_datetime.strftime('%Y-%m-%d %H:%M'), task_id)
    if error_info:
        body += u'%s肉机触发任务失败，请登陆机器手动执行' %(','.join(error_info))
    else:
        body += u'全部肉机已马力全开～'

    send_email(to_addrs, 'preload task info', body)
