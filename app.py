# -*- coding: utf-8 -*- 
import os, sys
import sqlite3
from flask import Flask, request, g
from threading import Thread
from wit import Wit
from pymessenger import Bot
from pymessenger.user_profile import UserProfileApi
#from twilio.rest import Client
from otak import Otak
from datetime import date
import time
import requests
import json
import random
import socket
import locale
import paramiko 

locale.setlocale(locale.LC_ALL, '')
app = Flask(__name__)

"""
Konstanta untuk pengecekan server Manzada
"""
SERVER = "app.manzada.net"
KANTOR = "kantor.manzada.store"
WEBPORT = 8069
BPORT = 22201
DPORT = 22202
TIMEOUT = 30
RETRY = 1


PAGE_ACCESS_TOKEN = "EAAFDKXr10PgBANKs4ZB7iWI0CLXdQNPHunnZBLCIWwAFRLfQtG8GOdZARaFxpiplyB9SoUS0BXHyRl6mrxM5vyJ77jcj8ygOPaemZBETZBHn43qlfFZAUFVHywh6gSbXRWZC2k9LTAsxyzSrVnlOC29RSEZC1cqPUKfHq3pxsouFU6hvSY6gL4XGB7EZC6YwNpSoZD"
#WIT_TOKEN = "B2A3KZPWQ547ESN7JOCHVLTTWUDA4JJQ"
WIT_TOKEN = "7TZIFRUFCT4SW3WIHRAZMBFW4QZOYUHE"
bot = Bot(PAGE_ACCESS_TOKEN)
otak=Otak()
profile = UserProfileApi(PAGE_ACCESS_TOKEN)
last_topic = None
start_monitor=False

TWILIO_ACCOUNT_SID = 'AC213eab4d468bea5cbb71ccbdceeecf28'
TWILIO_AUTH_TOKEN = '470ee0c21a6d8997dbe1b4368ff214ed'

def buatData():
    conn_sqlite=False
    try:
        conn_sqlite = sqlite3.connect("state.db")
        clite=conn_sqlite.cursor()
        #clite.execute("DROP TABLE IF EXISTS state_bayar")
        #clite.execute("CREATE TABLE IF NOT EXISTS state_bayar (\
        #                 fb_id text PRIMARY KEY, \
        #                 no_faktur text,\
        #                 jumlah_bayar text,\
        #                 state text)")
        clite.execute("DROP TABLE IF EXISTS state_type")
        clite.execute("CREATE TABLE IF NOT EXISTS state_type (\
                         fb_id text, \
                         kalimat text)")
        conn_sqlite.commit()
    except (Exception, sqlite3.Error) as error:
        return False
    finally:
        if(conn_sqlite):
            clite.close()
            conn_sqlite.close()
            return True
buatData()

def broadcast(tipe):
    nama="Boss"
    fb_ids=['3432901240109402'] #yme 
    fb_idsx=['3432901240109402', #me
            '3711661985518877', #boss
            '3164557827000038', #dani
            '3706874686003580', #tedi
            '3941390309222663', #ahmad
            '3264582853639869', #rian
            '4345408962193459', #ghiew
            '4937492586295334', #agung baru
            '4294487443937631', #adi
            '3364431640310686', #zul
            '25176516441947351'] #yayat 
    #'3322796671143503', #agung lama
    bot_id='106014174607450'

    for fb_id in fb_ids:
        nama="Sob" #get_first_name(fb_id)
        if fb_id=='3711661985518877' or fb_id=='3432901240109402':
            nama="Boss"
        text=random_notif(tipe, nama)
        if fb_id != '106014174607450':
            fb_message(fb_id, bot_id, "typing_on", text)

def random_notif(tipe, nama="Boss"):
    notif=[]
    if tipe=='online':
        notif=["{}. Sekarang server sudah online :)",
                "{}. Perbaikan sudah selesai, Server online.",
                "{}. Maaf sudah menunggu, server sudah online sekarang",
                "{}. Server sudah online, selamat melanjutkan pekerjaan!"]
    if tipe=='offline':
        notif=["Maaf {}. Server offline. 🙏🏻",
                "{} Server offline. kami mohon maaf atas ketidaknyamanannya 🙏🏻",
                "{} Server offline. Rin akan mencoba memperbaikinya, ditunggu ya..",
                "Maaf {}. Server sedang offline, Jika sudah online, akan Rin infokan."]
    random.shuffle(notif)
    return notif[0].format(nama)

def get_first_name(fb_id):
    nama=""
    info=profile.get(fb_id, fields="name")
    nama=info.get("first_name")
    print("USER INFO : " + str(info))
    return nama

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('state.db')
    return db

def query_db(query, one=False, commit=False):
    cur = get_db().execute(query)
    rv = cur.fetchall()
    if commit:
        get_db().commit()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET'])
def verify():
        # Webhook verification
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == "hello":
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    log(data)
    if data['object'] == 'page':
        for entry in data['entry']:
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    # IDs
                    sender_id = messaging_event['sender']['id']
                    recipient_id = messaging_event['recipient']['id']
                    if messaging_event.get('message'):
                        # Extracting text message
                        if 'text' in messaging_event['message']:
                            messaging_text = messaging_event['message']['text']
                        else:
                            messaging_text = 'no text'

                        response = None
                        response = client.message(messaging_text)
                        #if sender_id != '3981979258485853':
                        if sender_id != '3164557827000038sasas':
                            handle_message_future(response, sender_id, recipient_id)
                        else:
                            fb_message(sender_id, '106014174607450', "typing_on", "You are typing the same words too many times in a short time a.k.a SPAM. Because of this the messenger is temporarily blocking you. if it is because you are checking the server too often (in seconds), give the server time to fix, everything needs processing")
            else:
                # Returned another event
                return 'Received Different Event'
    else:
        # Returned another event
        return 'Received Different Event'
    return "ok", 200

def use_thread(func, response, value, fb_id, nama):
    thread = Thread(target=use_threaded, args=(func, response, value, fb_id, nama,))
    thread.daemon = True
    print("START THREAD ...")
    thread.start()
    print("THREAD DONE.")

def use_threaded(func, response, value, fb_id, nama):
    print("Im Here 1")
    #fb_id='3364431640310686'
    text=""
    obj=func(response, value, fb_id, nama)
    if isinstance(obj, list):
        print("HERE 2")
        count=0
        max_count=0
        for row in range(len(obj)):
            count+=1
        print("COUNT : "+str(count))
        if count > 9:
            warning="Dikarenakan jumlah baris data terlalu banyak\nAgar tampilan lebih mudah dibaca\nRin akan membagi pesan menjadi beberapa halaman"
            fb_message(fb_id, '106014174607450', "typing_on", warning)
            max_count=count
            count=0
            step=0
            page=1
            print("HERE 3")
            for x in range(len(obj)):
                count+=1
                step+=1
                text=text+obj[x]+'\n'
                if count==9 or step==max_count:
                    print(text)
                    fb_message(fb_id, '106014174607450', "typing_on", text)
                    text=""
                    count=0
                    page+=1
        else:
            for x in range(len(obj)):
                text=text+obj[x]+'\n'
            fb_message(fb_id, '106014174607450', "typing_on", text)
    else:
        print("Im Here Last")
        if value=="whatsapp":
            #kirim_whatsapp(obj, fb_id)
            notif_kantor(obj, DPORT, 'dani')
            #notif_kantor(obj, BPORT, 'b')
        else:
            fb_message(fb_id, '106014174607450', "typing_on", obj)

def thread_monitor_server():
    thread = Thread(target=threaded_monitor_server)
    thread.daemon = True
    print("START THREAD ...")
    thread.start()
    print("THREAD DONE.")

def threaded_monitor_server():
    print("Im Here 1")
    stat=True
    while True:
        if otak.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            if stat==False:
                stat=True
                broadcast("online")
        else:
            if stat==True:
                stat=False
                broadcast("offline")
    print("Im Here Last")

def kirim_whatsapp(pesan, to):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
                              body=pesan,
                              from_='whatsapp:+14155238886',
                              to='whatsapp:'+to
                          )

def notif_kantor(pesan, port, user):
    if otak.check_server(KANTOR, port, TIMEOUT, RETRY):
        print("Send notif to kantor...")
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(KANTOR, port, user, 'a')
            cli="""echo '{}' > /home/{}/STOCK-WARNING.txt && DISPLAY=:0 kate /home/{}/STOCK-WARNING.txt""".format(pesan, user, user)
            stdin, stdout, stderr = ssh.exec_command(cli)
            print("Notif to kantor sent.")
            lines = stdout.readlines()
            print(lines)
        finally:
            if ssh:
                ssh.close()
                print("SSH Closed.")
    else:
        print("SEND NOTIF KANTOR FAILED : PRIVATE IP?")

def send_typing_bubble(sender_id, recipient_id, action, response_sent_text):
    bot.send_action(sender_id, action)
    time.sleep(5)
    if sender_id=='106014174607450':
        return None
    bot.send_text_message(sender_id, response_sent_text)

def fb_message(sender_id, recipient_id, action, text):
    """
    Fungsi untuk mengembalikan respon ke messenger
    """
    # Send POST request to messenger
    resp=send_typing_bubble(sender_id, recipient_id, action, text)
    return resp

def say_wait(sender_id, waiting_word):
    bot.send_action(sender_id, 'typing_on')
    time.sleep(3)
    bot.send_text_message(sender_id, waiting_word)

def handle_message_future(response, fb_id, recipient_id):
    text=None
    value=None
    nama=None
    pemalas=False
    commands=False
    gm_commands=False
    bertanya=False
    salam=False
    greet=False
    maaf=False
    thanks=False
    praise=False
    fb_ids=['3432901240109402', #me
            '3711661985518877', #boss
            '3164557827000038', #dani
            '3706874686003580', #tedi
            '3941390309222663', #ahmad
            '3264582853639869', #rian
            '4345408962193459', #ghiew
            '4937492586295334', #agung
            '4294487443937631', #adi
            '3364431640310686', #zul
            '25176516441947351'] #yayat
    #black_listed=['3322796671143503', # Agung
    #              '3164557827000038'] # Dani
    my_master='3432901240109402'
    nama="Sob"#get_first_name(fb_id)
    #url = 'http://freegeoip.net/json/{}'.format(request.remote_addr)
    #r = requests.get(url)
    #j = json.loads(r.text)
    #city = j['city']
    #print("Lokasi : " + city)
    if fb_id in ['3432901240109402', '3711661985518877']:
        nama="Boss"
    try:
        print("RESPONSE : " + str(response))
        print("Nama : " + str(nama))
        if 'entities' in response: #and (fb_id not in black_listed):
            body=[]
            if '_text' in response:
                body=response['_text'].split(' ')
            pemalas=len(body) <= 2
            entities=response['entities']
            bertanya='tanya_type' in entities
            salam='salam_type' in entities
            greet='greetings_type' in entities
            maaf='maaf_type' in entities
            thanks='thanks_type' in entities
            praise='praise_type' in entities
            commands='commands_type' in entities
            gm_commands='gm_commands_type' in entities
            object_type='object_type' in entities
            #------------ General Activities ------------------------------------
            if salam:
                text="wa'alaikumsalam"
            if greet:
                if bertanya:
                    greet=False
                value=get_value(entities,'greetings_type')
                text=otak.get_greeting(value, fb_id, nama)
            if maaf:
                if not commands:
                    text="Gpp {}".format(nama)
            if thanks:
                value=get_value(entities,'thanks_type')
                text=otak.get_thanks(value, fb_id, nama)
            if praise:
                value=get_value(entities,'praise_type')
                if not greet and not commands:
                    text=otak.get_pujian(value, fb_id, nama)
            if commands:
                value=get_value(entities,'commands_type')
                if value=="rekomendasi":
                    text="Sebentar ya..."
                if value=="faktur pajak":
                    text="Eenie, Meenie, Miney, Mo.. :)"
                if value=="abrakadabra":
                    text="Abrakadabra..."
                if value=="draft":
                    text="Rin membutuhkan waktu untuk menghitung draft faktur... tunggu sebentar.."
                if value=="insentif":
                    if object_type:
                        o=get_value(entities, 'object_type')
                        if o=="faktur":
                            text="Sebentar Rin hitung total faktur.."
                use_thread(otak.get_commands, response, value, fb_id, nama)
                if value=="push":
                    #use_thread(otak.get_warning_stok, response, 'whatsapp', '+6281395784190', nama) #W.A Boss
                    use_thread(otak.get_warning_stok, response, 'whatsapp', '+6282317066835', nama) #W.A Dani
            if gm_commands:
                value=get_value(entities,'gm_commands_type')
                if value=="start_monitor_server":
                    thread_monitor_server()
            #-------------------------------------------------------------------

            #-------- [S][P][O][K] Activities ----------------------------------
            if (not commands) and (not gm_commands) and (not salam) and (not greet) and (not maaf) and (not thanks) and (not praise):
                kalimat="238901287347412040128312903102398"
                if '_text' in response:
                    kalimat=response['_text']
                state_kalimat = query_db("select kalimat from state_type where fb_id='{}' and kalimat='{}'".format(fb_id, kalimat), one=True)
                if state_kalimat is None:
                    save_kalimat=query_db("insert into state_type (fb_id, kalimat) values('{}','{}')".format(fb_id, response['_text']), one=True, commit=True)
                    state_kalimat = query_db("select kalimat from state_type where fb_id='{}'".format(fb_id), one=True)
                    text=otak.analisa_kalimat(response, value, fb_id, nama)
                else:
                    query_db("delete from state_type where fb_id='{}'".format(fb_id), one=True, commit=True)
                    rsp=["Kenapa kamu mengetikan kalimat yang sama?","pertanyaan yang sama? hmmm.."]
                    random.shuffle(rsp)
                    text=rsp[0]
    except:
        print("Ada soket error : " + sys.exc_info()[0])
        pass
    if text:
        print("GOOD")
        fb_message(fb_id, recipient_id, "typing_on", text)

def get_value(entities, entity):
    return entities[entity][0]['value']

def log(message):
    print(message)
    sys.stdout.flush()

# Setup Wit Client
client = Wit(access_token=WIT_TOKEN)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug = False, use_reloader=False, port=80)#debug = True, port = 80)

