# -*- coding: utf-8 -*- 
import psycopg2
import odoorpc
import datetime
import time
import requests, json
import random
import locale
import operator
import socket
from dateutil.relativedelta import relativedelta

locale.setlocale(locale.LC_ALL, '')
IAM='3432901240109402'
SERVER = "app.manzada.net"
WEBPORT = 8069
TIMEOUT = 3
RETRY = 1

#|| '%' AS x_pencapaian \
param_sql =""
sql_insentif_salesman = "SELECT \
            concat(\
            (SELECT name FROM product_template WHERE name=t.x_name), \
            '(', x_komisi_produk::text, '/', x_target::text, ')') as x_nama_produk, \
            x_total_terjual,\
            round((CASE WHEN x_target >0 THEN \
            ((x_total_terjual/x_target)*100) \
            ELSE \
            0 \
            END),2) as x_persen_pencapaian,\
            (x_total_terjual * \
            CASE WHEN SUM(x_total_terjual) OVER (window_bersih) >= x_target * 80/100 THEN \
            x_komisi_produk \
            ELSE \
            0 \
            END) as x_insentif \
            FROM(\
            SELECT \
            name as x_name, \
            (SELECT user_id FROM account_invoice WHERE id=ail.invoice_id) as x_user_id,\
            (SELECT target_penjualan FROM product_template WHERE id = (select product_tmpl_id from product_product where id=ail.product_id)) as x_target,\
            (SELECT komisi_produk FROM product_template WHERE id = (select product_tmpl_id from product_product where id=ail.product_id)) as x_komisi_produk,\
            SUM(quantity) as x_total_terjual \
            FROM account_invoice_line ail \
            WHERE invoice_id IN (SELECT id FROM account_invoice WHERE state IN ('open', 'paid') \
            and type='out_invoice' \
            and user_id = {} and date_trunc('month', date_invoice) = date_trunc('month', current_date)) \
            AND name IN (SELECT name FROM product_template WHERE target_penjualan > 0) \
            AND uos_id IN (SELECT id FROM product_uom WHERE uom_type='reference') \
            GROUP BY x_user_id, x_name, ail.name, ail.product_id \
            )t \
            WINDOW window_bersih AS (PARTITION BY t.x_name, t.x_user_id)"

sql_insentif_salesman_by_date = "SELECT \
            concat(\
            (SELECT name FROM product_template WHERE name=t.x_name), \
            '(', x_komisi_produk::text, '/', x_target::text, ')') as x_nama_produk, \
            x_total_terjual,\
            round((CASE WHEN x_target >0 THEN \
            ((x_total_terjual/x_target)*100) \
            ELSE \
            0 \
            END),2) as x_persen_pencapaian,\
            (x_total_terjual * \
            CASE WHEN SUM(x_total_terjual) OVER (window_bersih) >= x_target * 80/100 THEN \
            x_komisi_produk \
            ELSE \
            0 \
            END) as x_insentif \
            FROM(\
            SELECT \
            name as x_name, \
            (SELECT user_id FROM account_invoice WHERE id=ail.invoice_id) as x_user_id,\
            (SELECT target_penjualan FROM product_template WHERE id = (select product_tmpl_id from product_product where id=ail.product_id)) as x_target,\
            (SELECT komisi_produk FROM product_template WHERE id = (select product_tmpl_id from product_product where id=ail.product_id)) as x_komisi_produk,\
            SUM(quantity) as x_total_terjual \
            FROM account_invoice_line ail \
            WHERE invoice_id IN (SELECT id FROM account_invoice WHERE state IN ('open', 'paid') \
            and type='out_invoice' \
            and user_id = {} and (date_invoice >= '{}' and date_invoice <= '{}')) \
            AND name IN (SELECT name FROM product_template WHERE target_penjualan > 0) \
            AND uos_id IN (SELECT id FROM product_uom WHERE uom_type='reference') \
            GROUP BY x_user_id, x_name, ail.name, ail.product_id \
            )t \
            WINDOW window_bersih AS (PARTITION BY t.x_name, t.x_user_id)"

sql_omzet = "SELECT \
            x_user_id, \
            x_total_omzet, \
            round((coalesce(x_total_omzet,0)/\
            (CASE \
            WHEN x_user_id  = 5 THEN 3427200000 \
            WHEN x_user_id = 31 THEN 2632000000 \
            WHEN x_user_id = 7 THEN 1904000000 \
            WHEN x_user_id = 9 THEN 2260000000 \
            WHEN x_user_id = 44 THEN 1288000000 \
            WHEN x_user_id = 6 THEN 1288000000 \
            WHEN x_user_id = 56 THEN 1880800000 \
            ELSE 800000000 END)*100),2) as x_pencapaian \
            FROM \
            (SELECT \
            user_id as x_user_id, \
            SUM(amount_total) filter (WHERE  (state ='open' or state='paid') and type='out_invoice' and date_trunc('month', date_invoice) = date_trunc('month', current_date)) \
            AS x_total_omzet \
            FROM account_invoice \
            WHERE user_id=5 or user_id=7 or user_id=9 or user_id=31 or user_id=44 or user_id=6 or user_id=56 \
            GROUP BY x_user_id \
            )t \
            WINDOW window_bersih AS (PARTITION BY t.x_user_id) \
            ORDER BY x_pencapaian DESC"

sql_omzet_by_date_detail = "SELECT \
            x_user_id, \
            x_total_omzet, \
            round((coalesce(x_total_omzet,0)/\
            (CASE \
            WHEN x_user_id  = 5 THEN 3427200000 \
            WHEN x_user_id = 31 THEN 2632000000 \
            WHEN x_user_id = 7 THEN 1904000000 \
            WHEN x_user_id = 9 THEN 2260000000 \
            WHEN x_user_id = 44 THEN 1288000000 \
            WHEN x_user_id = 6 THEN 1288000000 \
            WHEN x_user_id = 56 THEN 1880800000 \
            ELSE 800000000 END)*100),2) as x_pencapaian \
            FROM \
            (SELECT \
            user_id as x_user_id, \
            SUM(amount_total) filter (WHERE  (state ='open' or state='paid') and type='out_invoice' and (date_invoice >= '{}' and date_invoice <= '{}')) \
            AS x_total_omzet \
            FROM account_invoice \
            WHERE user_id=5 or user_id=7 or user_id=9 or user_id=31 or user_id=44 or user_id=6 or user_id=56 \
            GROUP BY x_user_id \
            )t \
            WINDOW window_bersih AS (PARTITION BY t.x_user_id) \
            ORDER BY x_pencapaian DESC"

sql_omzet_harian ="""
SELECT 
SUM(amount_total) as total 
FROM account_invoice
WHERE 
user_id={} 
and state IN ('open','paid', 'draft')
and type = 'out_invoice'
and date_invoice=current_date
"""

sql_omzet_by_date ="""
SELECT
SUM(amount_total) as total
FROM account_invoice
WHERE 
state in ('open', 'paid')
and type = 'out_invoice'
and (date_invoice >= '{}' and date_invoice <= '{}')
"""

sql_pembelian_by_date ="""
SELECT
SUM(amount_total) as total
FROM account_invoice
WHERE 
state in ('open', 'paid')
and type = 'in_invoice'
and (date_invoice >= '{}' and date_invoice <= '{}')
"""

sql_residual ="""
SELECT
SUM(residual) as saldo
FROM account_invoice
WHERE 
state in ('open')
and type = 'out_invoice'
"""

sql_hutang ="""
SELECT
SUM(residual) as saldo
FROM account_invoice
WHERE 
state in ('open')
and type = 'in_invoice'
"""

sql_product_sale_history="select \
            product_id from account_invoice_line ail \
            where \
            invoice_id in (select id from account_invoice ai where \
            user_id={} \
            and partner_id={} \
            and type='out_invoice' and state in ('open', 'paid') \
            and date_invoice >= '{}' and date_invoice <= '{}') \
            group by ail.product_id"
sql_product_sale_history_boss="select \
            product_id from account_invoice_line ail \
            where \
            invoice_id in (select id from account_invoice ai where \
            partner_id={} \
            and type='out_invoice' and state in ('open', 'paid') \
            and date_invoice >= '{}' and date_invoice <= '{}') \
            group by ail.product_id"
sql_product_sale_history_sum="""
select product_id, 
case when ((sum(quantity))/3)<1 then 1 else (sum(quantity))/3 end as total 
from account_invoice_line ail 
where invoice_id in (select id from account_invoice ai where user_id={} 
and partner_id={}  
and type='out_invoice' and state in ('open', 'paid') and date_invoice >= '{}' and date_invoice <= '{}')
group by ail.product_id order by total desc
"""
sql_product_sale_history_sum_boss="""
select product_id,
case when ((sum(quantity))/3)<1 then 1 else (sum(quantity))/3 end as total
from account_invoice_line ail
where invoice_id in (select id from account_invoice ai where 
partner_id={}
and type='out_invoice' and state in ('open', 'paid') and date_invoice >= '{}' and date_invoice <= '{}')
group by ail.product_id order by total desc
"""
sql_product_sale_history_sum_="""
select product_id, (sum(quantity)) as total from account_invoice_line ail
where invoice_id in (select id from account_invoice ai where user_id={}
and partner_id={}
and type='out_invoice' and state in ('open', 'paid') and date_invoice >= '2020 09 01' and date_invoice <= '2020 09 30')
group by ail.product_id order by total desc
"""
sql_progress_sale="""
select product_id, (sum(quantity)) as total from account_invoice_line ail
where invoice_id in (select id from account_invoice ai where user_id={}
and partner_id={}  
and type='out_invoice' and state in ('draft', 'open', 'paid') and date_trunc('month', date_invoice) = date_trunc('month', current_date))
group by ail.product_id order by total desc
"""
sql_progress_sale_boss="""
select product_id, (sum(quantity)) as total from account_invoice_line ail
where invoice_id in (select id from account_invoice ai where 
partner_id={}
and type='out_invoice' and state in ('draft', 'open', 'paid') and date_trunc('month', date_invoice) = date_trunc('month', current_date))
group by ail.product_id order by total desc
"""
sql_get_partner_id="""
select id from res_partner where active=True and customer=True and name ilike '{}%' limit 1
"""
sql_status_order="select (select name from res_partner where id=so.partner_id) as toko, amount_total as total, state as status from sale_order so where user_id={} and state in ('draft', 'done', 'progress') and date_trunc('day', create_date) = date_trunc('day', now()) order by create_date DESC;"
sql_faktur_by_number="select id, number, (select name from res_partner where id=ai.partner_id) as toko, residual, amount_total \
        from account_invoice ai where number='{}' and state='open' and type='out_invoice'"
sql_id_faktur="select id from account_invoice where number='{}'"
sql_saldo_faktur="select residual from account_invoice where number='{}'"
sql_get_period="select id from account_period where code = '{}'"

sql_insentif_terigu="""
SELECT pengirim, sum(CASE WHEN (SELECT kondektur FROM stock_move WHERE id=ail.move_id) = '' THEN ail.quantity*250 ELSE ((ail.quantity)*250)/2 END)::int FROM (SELECT id, supir as pengirim FROM stock_move UNION SELECT id, kondektur as pengirim FROM stock_move) tsm, account_invoice_line ail WHERE ail.product_id IN (SELECT id FROM product_product WHERE default_code IN ('TSB', 'BSB25', 'BSM25', 'F10H25', 'TGE25', 'HKRB25', 'JWR25', 'TKM25', 'TRP', 'TRL', 'TRT', 'GLVI', 'ACAS')) AND invoice_id IN (SELECT id FROM account_invoice WHERE type='out_invoice' AND state IN ('open', 'paid') AND date_trunc('month', date_invoice)=date_trunc('month', current_date)) AND tsm.id=ail.move_id AND pengirim is not null GROUP BY pengirim ORDER BY pengirim;
"""
sql_insentif_gula="""
SELECT pengirim, sum(CASE WHEN (SELECT kondektur FROM stock_move WHERE id=ail.move_id) = '' THEN ail.quantity*500 ELSE ((ail.quantity)*500)/2 END)::int FROM (SELECT id, supir as pengirim FROM stock_move UNION SELECT id, kondektur as pengirim FROM stock_move) tsm, account_invoice_line ail WHERE ail.product_id IN (SELECT id FROM product_product WHERE default_code IN ('G SMT', 'GPR', 'VIT50')) AND invoice_id IN (SELECT id FROM account_invoice WHERE type='out_invoice' AND state IN ('open', 'paid') AND date_trunc('month', date_invoice)=date_trunc('month', current_date)) AND tsm.id=ail.move_id AND pengirim is not null GROUP BY pengirim ORDER BY pengirim;
"""

sql_insentif_terigu_by_date="""
SELECT pengirim, sum(CASE WHEN (SELECT kondektur FROM stock_move WHERE id=ail.move_id) = '' THEN ail.quantity*250 ELSE ((ail.quantity)*250)/2 END)::int FROM (SELECT id, supir as pengirim FROM stock_move UNION SELECT id, kondektur as pengirim FROM stock_move) tsm, account_invoice_line ail WHERE ail.product_id IN (SELECT id FROM product_product WHERE default_code IN ('TSB', 'BSB25', 'BSM25', 'F10H25', 'TGE25', 'HKRB25', 'JWR25', 'TKM25', 'TRP', 'TRL', 'TRT', 'GLVI', 'ACAS')) AND invoice_id IN (SELECT id FROM account_invoice WHERE type='out_invoice' AND state IN ('open', 'paid') and (date_invoice >= '{}' and date_invoice <= '{}')) AND tsm.id=ail.move_id AND pengirim is not null GROUP BY pengirim ORDER BY pengirim;
"""
sql_insentif_gula_by_date="""
SELECT pengirim, sum(CASE WHEN (SELECT kondektur FROM stock_move WHERE id=ail.move_id) = '' THEN ail.quantity*500 ELSE ((ail.quantity)*500)/2 END)::int FROM (SELECT id, supir as pengirim FROM stock_move UNION SELECT id, kondektur as pengirim FROM stock_move) tsm, account_invoice_line ail WHERE ail.product_id IN (SELECT id FROM product_product WHERE default_code IN ('G SMT', 'GPR', 'VIT50')) AND invoice_id IN (SELECT id FROM account_invoice WHERE type='out_invoice' AND state IN ('open', 'paid') and (date_invoice >= '{}' and date_invoice <= '{}')) AND tsm.id=ail.move_id AND pengirim is not null GROUP BY pengirim ORDER BY pengirim;
"""

sql_product_sales="""
SELECT (CASE WHEN left(name,1)='[' THEN ltrim(split_part(name, ']', 2)) ELSE name END) AS nama, SUM(quantity) FROM account_invoice_line ail WHERE name ilike '%{}%' AND invoice_id IN (SELECT id FROM account_invoice WHERE state IN ('open', 'paid') AND type='out_invoice' AND (date_invoice >= '{}' AND date_invoice <= '{}')) GROUP BY nama ORDER BY 1;
"""
sql_product_sales_salesman="""
SELECT (CASE WHEN left(name,1)='[' THEN ltrim(split_part(name, ']', 2)) ELSE name END) AS nama, SUM(quantity) FROM account_invoice_line ail WHERE name ilike '%{}%' AND invoice_id IN (SELECT id FROM account_invoice WHERE state IN ('open', 'paid') AND type='out_invoice' AND (date_invoice >= '{}' AND date_invoice <= '{}') AND user_id = {}) GROUP BY nama ORDER BY 1;
"""


#---------------------------
# FOR BKP ONLY
#----------------------------------
sql_product_sale_bkp_boss="select \
product_id, name, sum(quantity) as kts, sum(price_subtotal) as subtotal, \
(select price_unit from account_invoice_line where invoice_id in \
(select id from account_invoice where type = 'in_invoice' and state in ('draft', 'open', 'paid') \
and partner_id in (708, 733, 732)) \
and product_id=ail.product_id \
order by create_date desc limit 1 \
) as modal \
from account_invoice_line ail \
where \
invoice_id in (select id from account_invoice ai where ai.partner_id={} \
and type='out_invoice' \
and state in ('open', 'paid') and date_invoice >= '{}' \
and date_invoice <= '{}') \
and ail.product_id in (select product_id from account_invoice_line where invoice_id in \
(select id from account_invoice where type = 'in_invoice' and state in ('draft', 'open', 'paid') \
and partner_id in (708, 733, 732))) \
group by ail.product_id, ail.name"

class Otak:

    def tcpCheck(self, ip, port, timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((ip, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            return True
        except:
            return False
        finally:
            s.close()

    def check_server(self, ip, port, timeout, retry):
        ipup = False
        for i in range(retry):
            if self.tcpCheck(ip, port, timeout):
                ipup = True
                break
            else:
                print("Tidak terhubung...")
                time.sleep(timeout)
        return ipup

    def sql_query(self, sql):
        conn_serv=False
        record=False
        try:
            conn_serv=psycopg2.connect(user="offline",
                    password="ra#asia",
                    host=SERVER,
                    port="5432",
                    database="manzada")
            cursor=conn_serv.cursor()
            cursor.execute(sql)
            record=cursor.fetchall()
        except (Exception, psycopg2.Error) as error:
            print(error)
            return False
        finally:
            if(conn_serv):
                cursor.close()
                conn_serv.close()
                return record

    def random_wait(self, noanswer=False):
        waiting_word=["sebentar..", "kedap..", "antosan kdap..", "", "ok 👌🏻", "siap", "ditunggu ya..", "mangga..", "", "okhay 👌🏻", "otre 👌🏻", "ashiaap", "", "bentar..", ""]
        if noanswer:
            waiting_word=["sebentar..", "kedap..", "antosan kdap..", "", "ditunggu ya..","", "bentar..", ""]
        random.shuffle(waiting_word)
        return waiting_word[0]

    def get_greeting(self, value=None, fb_id=None, nama=None):
        text = None
        try:
            now = datetime.datetime.now()
            hour = now.hour
            #waktu=self.get_waktu(hour)
            response = ["Hai {}. ", "Hello {}. ", "Hey {}. ", "Halo {}. "]
            response_body = ["Ada yang bisa Rin bantu?", "Ada apa?", "What's Up?"]
            random.shuffle(response)
            random.shuffle(response_body)
            if value=="pagi" or value=="siang" or value=="malam":
                waktu=self.get_part_of_day(datetime.datetime.now().hour)
                if value != waktu:
                    print(datetime.datetime.now())
                    text = """
Sekarang itu {} {}. :)
Setelah Rin analisa, menggunakan rumus:
BH=CX2xT5x..blah.. blah.. blah..
ternyata kamu itu tipikal pembohong.
""".format(waktu, nama)
                else:
                    text=value + " {} :)".format(nama)
            else:
                text = response[0].format(nama) + response_body[0]
        except:
            pass
        return text
    
    def get_thanks(self, value=None, fb_id=None, nama=None):
        text = None
        try:
            response = ["OK {}. Good luck!", "Sama-sama {}. :) ", "OK {}. Tetap semangat!", "Siap {}.", ":)", "Sami nuhun {} :)", "Sami-sami {}.", "Sawangsulna :)", "Anytime {}. :)"]
            random.shuffle(response)
            text = response[0].format(nama)
        except:
            pass
        return text

    def get_goodbye(self, value=None, fb_id=None, nama=None):
        text = None
        try:
            response = ["OK {}. Good luck!", "OK {}. Tetap semangat!"]
            random.shuffle(response)
            text = response[0].format(nama)
        except:
            pass
        return text

    def get_status_order(self, fb_id, nama):
        text=""
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                if 'sale.order' in odoo.env:
                    current_date = datetime.date.today()
                    user_id=self.get_manzada_user_id(fb_id)
                    sale_order = odoo.env['sale.order']
                    print("get_so HERE 3")
                    sale_order_ids = sale_order.search([('state', 'in', ['draft','progress','done']),('user_id', '=', user_id),('date_order','>=', str(current_date) + ' 00:00:00')])
                    print("get_so HERE 4")
                    if sale_order_ids:
                        for order in sale_order.browse(sale_order_ids):
                            toko=order.partner_id.name
                            amount_total=order.amount_total
                            status=order.state
                            text=text+"""
{}
Total  : {}
Status : {}""".format(toko, locale.format("%d", amount_total, 1), status)
                    else:
                        text="Maaf. Rin tidak bisa menemukan list order."
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_pujian(self, value, fb_id, nama):
        text = ""
        resp = ["Makasih {} :)", "Terima kasih {}. :)", "Thanks {}. :)", "Makasih {}. :) Rin akan terus belajar", "Thank You {}. :)", "Hatur nuhun {}. :)"] 
        random.shuffle(resp)
        text=resp[0].format(nama)
        return text

    def get_stok(self, response, value, fb_id, nama):
        text=""
        nama_barang=""
        if '_text' in response:
            body=response['_text'].split(' ', 2)
        if len(body) == 3 :
            nama_barang=body[2]
            if len(nama_barang) >= 3:
                try:
                    if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                        # Prepare the connection to the server
                        odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                        # Login
                        odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                        print("HERE 2")
                        if 'product.template' in odoo.env:
                            product_template = odoo.env['product.template']
                            product_supplierinfo = odoo.env['product.supplierinfo']
                            print("HERE 3")

                            products = product_template.search([('name', 'ilike', '%{}%'.format(nama_barang))])
                            if nama_barang=="gbp":
                                gbp_pids=[]
                                gbp_products = product_supplierinfo.search([('name', '=', 1783)])
                                for pid in product_supplierinfo.browse(gbp_products):
                                    gbp_pids.append(pid.product_tmpl_id)
                                print(gbp_pids)
                                products = product_template.search([('id', 'in', gbp_pids)])
                            print("Here 4")
                            if products:
                                for product in product_template.browse(products):
                                    nama_produk=product.name
                                    qty_available=product.qty_available
                                    virtual_available=product.virtual_available
                                    rma_available=product.rma_available
                                    rma_virtual_available=product.rma_virtual_available
                                    text=text+"""
{}
On Hand         : {}
Perkiraaan      : {}""".format(nama_produk, locale.format("%d", qty_available, 1), locale.format("%d", virtual_available, 1)) + '\n'
                            else:
                                text="{}. Maaf Rin tidak bisa menemukan produk dengan nama seperti {}".format(nama, nama_barang)
                    else:
                        text=self.get_server_exception("ambil_data", nama)
                except:
                    #print("Ada soket error : " + sys.exc_info()[0])
                    text="Gagal memproses data, silahkan dicoba lagi.."
            else:
                text="Nama barang minimal 3 huruf"
        else:
            text="Maaf. {} mau cek stok apa?".format(nama)
        return text

    def get_rekomendasi(self, response, value, fb_id, nama):
        result=[]
        product_ids=[]
        if '_text' in response:
            body=response['_text'].split(' ', 1)
        if len(body) == 2 :
            toko=body[1]
            try:
                if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                    current_date = datetime.date.today()
                    str_first_date=str(current_date.year)+' '+str(current_date.month)+' 01'
                    a_three_month = relativedelta(months=3)
                    a_last_month = relativedelta(months=1)
                    first_date=datetime.datetime.strptime(str_first_date, '%Y %m %d')
                    first_three_month = first_date - a_three_month
                    first_last_month = first_date - a_last_month
                    last_month_date=datetime.date(first_last_month.year + (first_last_month.month == 12),
                    (first_last_month.month + 1 if first_last_month.month < 12 else 1), 1) - datetime.timedelta(1)
                    begin_date=str(first_three_month.year)+' '+str(first_three_month.month)+' 01'
                    end_date=str(last_month_date.strftime('%Y %m %d'))
                    print("BEGIN DATE : " + begin_date)
                    print("END DATE : " + end_date)

                    user_id=self.get_manzada_user_id(fb_id) #'3364431640310686')
                    record=self.sql_query(sql_get_partner_id.format(toko))
                    if record:
                        for row in record:
                            id_toko=int(row[0])
                        print("ID Toko :" + str(id_toko))
                        print("USER ID :" + str(user_id))
                        if nama=='Boss':
                            record_products=self.sql_query(sql_product_sale_history_boss.format(id_toko, begin_date, end_date))
                        else:
                            record_products=self.sql_query(sql_product_sale_history.format(user_id, id_toko, begin_date, end_date))
                        if record_products:
                            print("Rekom Here 2")
                            for product_id in record_products:
                                print("Rekom Here 3")
                                product_ids.append(product_id)
                            print("Rekom Here 4")
                            result=self.get_analisa_rekomendasi(response, value, fb_id, nama, product_ids, id_toko, begin_date, end_date)
                        else:
                            text="Maaf, Rin tidak bisa menemukan history produk.\nApakah Anda masuk kedalam user id Sales ?"
                            result.append(text)
                    else:
                        text="""
Maaf Rin tidak bisa menemukan nama toko yang mirip dengan {}
Silahkan periksa kembali penulisan nama toko
Harap diketahui, satu huruf atau spasi pun juga berpengaruh""".format(toko)
                        result.append(text)
                else:
                    text=self.get_server_exception("ambil_data", nama)
                    result.append(text)
            except:
                print("Ada soket error : " + sys.exc_info()[0])
                text="Gagal memproses data, silahkan dicoba lagi.."
                result.append(text)
        else:
            text="Untuk mendapatkan rekomendasi dari Rin,\nFormat penulisannya : rekomendasi<spasi>nama toko"
            result.append(text)
        return result

    def get_abrakadabra(self, response, value, fb_id, nama):
        result=[]
        product_ids=[]
        if '_text' in response:
            body=response['_text'].split(' ', 1)
        if len(body) == 2 :
            toko=body[1]
            try:
                if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                    current_date = datetime.date.today()
                    str_first_date=str(current_date.year)+' '+str(current_date.month)+' 01'
                    a_three_month = relativedelta(months=3)
                    a_last_month = relativedelta(months=1)
                    first_date=datetime.datetime.strptime(str_first_date, '%Y %m %d')
                    first_three_month = first_date - a_three_month
                    first_last_month = first_date - a_last_month
                    last_month_date=datetime.date(first_last_month.year + (first_last_month.month == 12),
                    (first_last_month.month + 1 if first_last_month.month < 12 else 1), 1) - datetime.timedelta(1)
                    begin_date=str(first_three_month.year)+' '+str(first_three_month.month)+' 01'
                    end_date=str(last_month_date.strftime('%Y %m %d'))
                    print("BEGIN DATE : " + begin_date)
                    print("END DATE : " + end_date)

                    user_id=self.get_manzada_user_id(fb_id) #'3364431640310686')
                    record=self.sql_query(sql_get_partner_id.format(toko))
                    if record:
                        for row in record:
                            id_toko=int(row[0])
                        print("ID Toko :" + str(id_toko))
                        print("USER ID :" + str(user_id))
                        if nama=='Boss':
                            record_products=self.sql_query(sql_product_sale_history_boss.format(id_toko, begin_date, end_date))
                        else:
                            record_products=self.sql_query(sql_product_sale_history.format(user_id, id_toko, begin_date, end_date))
                        if record_products:
                            print("Rekom Here 2")
                            for product_id in record_products:
                                print("Rekom Here 3")
                                product_ids.append(product_id)
                            print("Rekom Here 4")
                        result=self.get_analisa_abrakadabra(response, value, fb_id, nama, product_ids, id_toko, begin_date, end_date)
                    else:
                        text="""
Maaf Rin tidak bisa menemukan nama toko yang mirip dengan {}
Silahkan periksa kembali penulisan nama toko
Harap diketahui, satu huruf atau spasi pun juga berpengaruh""".format(toko)
                        result.append(text)
                else:
                    text=self.get_server_exception("ambil_data", nama)
                    result.append(text)
            except:
                print("Ada soket error : " + sys.exc_info()[0])
                text="Gagal memproses data, silahkan dicoba lagi.."
                result.append(text)
        else:
            text="Jika kamu merasa beruntung,\nFormat penulisannya : abrakadabra<spasi>nama toko"
            result.append(text)
        return result

    def get_analisa_rekomendasi(self, response, value, fb_id, nama, product_ids, id_toko, begin_date, end_date):
        result=[]
        filtered_ids=tuple()
        summary_history={}
        summary_progress={}
        print("get_analisa 1")
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                user_id=self.get_manzada_user_id(fb_id) #'3364431640310686')
                available_items=self.get_available_stok(response, value, fb_id, nama, product_ids, id_toko)
                print("get_analisa 2")
                if available_items:
                    print("get_analisa 3")
                    for key, values in available_items.items():
                        filtered_ids = filtered_ids + (key,)
                    print("filtered ids : "+str(filtered_ids))
                    if nama=='Boss':
                        record_history=self.sql_query(sql_product_sale_history_sum_boss.format(id_toko, begin_date, end_date))
                    else:
                        record_history=self.sql_query(sql_product_sale_history_sum.format(user_id, id_toko, begin_date, end_date))
                    print("Rec History :" + str(record_history))
                    for row in record_history:
                        if int(row[1]) < 10:
                            minimal=int(row[1])+2
                        else:
                            if nama=='Boss':
                                minimal=int(row[1])+(int(row[1])*(30/100))
                            if user_id==5:
                                minimal=int(row[1])+(int(row[1])*(30/100))
                            else:
                                minimal=int(row[1])+(int(row[1])*(30/100))
                        summary_history[row[0]]=minimal
                    print("get_analisa 5 : "+str(summary_history))
                    if nama=='Boss':
                        record_progress=self.sql_query(sql_progress_sale_boss.format(id_toko))
                    else:
                        record_progress=self.sql_query(sql_progress_sale.format(user_id, id_toko))
                    for row in record_progress:
                        progress=row[1]
                        summary_progress[row[0]]=progress
                    print("get_analisa 6 : "+str(summary_progress))
                    for key, values in available_items.items():
                        if summary_history.get(key):
                            if summary_progress.get(key):
                                progress=summary_progress.get(key)
                            else:
                                progress=0
                            product_name=values[0]
                            qty_available=values[1]
                            virtual_available=values[2]
                            minimal=summary_history.get(key)
                            print("MINIMAL QTY : " + str(minimal))
                            #progress=summary_progress.get(key)
                            print("PROGRESS : " + str(progress))
                            text="""
{}
Stok Fisik : {} 
Stok Perkiraan : {}
Progress/Minimal : {}/{}""".format(product_name, locale.format("%d", qty_available, 1), locale.format("%d", virtual_available, 1), locale.format("%d", progress, 1), locale.format("%d", minimal, 1))
                            result.append(text)
                            text=""
                else:
                    text="{}. Maaf Rin tidak bisa menemukan produk available".format(nama)
                    result.append(text)
            else:
                text=self.get_server_exception("ambil_data", nama)
                result.append(text)
        except:
            print("Ada soket error : " + sys.exc_info()[0])
            text="Gagal memproses data, silahkan dicoba lagi.."
            result.append(text)
        return result

    def get_analisa_abrakadabra(self, response, value, fb_id, nama, product_ids, id_toko, begin_date, end_date):
        result=[]
        filtered_ids=tuple()
        summary_history={}
        summary_progress={}
        print("get_analisa 1")
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                user_id=self.get_manzada_user_id(fb_id) #'3364431640310686')
                available_items=self.get_abrakadabra_stok(response, value, fb_id, nama, product_ids, id_toko)
                print("get_analisa 2")
                if available_items:
                    print("get_analisa 3")
                    for key, values in available_items.items():
                        filtered_ids = filtered_ids + (key,)
                    print("filtered ids : "+str(filtered_ids))
                    if nama=='Boss':
                        record_progress=self.sql_query(sql_progress_sale_boss.format(id_toko))
                    else:
                        record_progress=self.sql_query(sql_progress_sale.format(user_id, id_toko))
                    for row in record_progress:
                        progress=row[1]
                        summary_progress[row[0]]=progress
                    print("get_analisa 6 : "+str(summary_progress))
                    for key, values in available_items.items():
                        if summary_progress.get(key):
                            progress=summary_progress.get(key)
                        else:
                            progress=0
                        product_name=values[0]
                        qty_available=values[1]
                        virtual_available=values[2]
                        minimal=(int(values[1])/6)
                        if minimal<1:
                            minimal=2
                        print("MINIMAL QTY : " + str(minimal))
                        print("PROGRESS : " + str(progress))
                        text="""
{}
👐🏻
Stok Fisik : {}
Stok Perkiraan : {}
Progress/Minimal : {}/{}""".format(product_name, locale.format("%d", qty_available, 1), locale.format("%d", virtual_available, 1), locale.format("%d", progress, 1), locale.format("%d", minimal, 1))
                        result.append(text)
                        text=""
                else:
                    text="{}. Maaf Rin tidak bisa menemukan produk available".format(nama)
                    result.append(text)
            else:
                text=self.get_server_exception("ambil_data", nama)
                result.append(text)
        except:
            print("Ada soket error : " + sys.exc_info()[0])
            text="Gagal memproses data, silahkan dicoba lagi.."
            result.append(text)
        return result

    def get_abrakadabra_stok(self, response, value, fb_id, nama, product_ids, id_toko):
        text=""
        pilihan = list(range(1000))
        random.shuffle(pilihan)
        print("PILIHAN ARR : " + str(pilihan[0]))
        values=[]
        result={}
        print("get_available Here 1")
        try:
            user_id=self.get_manzada_user_id(fb_id)
            # Prepare the connection to the server
            odoo = odoorpc.ODOO('app.manzada.net', port=8069)
            odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
            print("get_available HERE 2")
            print("get_available PROD IDS : "+str(product_ids))
            if 'product.product' in odoo.env:
                product_product = odoo.env['product.product']
                print("get_available HERE 3")
                if product_ids:
                    products = product_product.search([('id', 'not in', product_ids), ('active', '=', 'True'),('virtual_available', '>=',1)], offset=int(pilihan[0]), limit=30)
                else:
                    products = product_product.search([('active', '=', 'True'),('virtual_available', '>=',1)], offset=int(pilihan[0]), limit=30)
                print("get_available Here 4")
                if products:
                    print("Get_available Here 5")
                    count=0
                    for product in product_product.browse(products):
                        count+=1
                        product_id=product.id
                        qty_available=product.qty_available
                        virtual_available=product.virtual_available
                        result[product_id]=[product.name, qty_available, virtual_available]
                else:
                    pass
            else:
                pass
        except:
            pass
        print(str(result))
        return result

    def get_available_stok(self, response, value, fb_id, nama, product_ids, id_toko):
        text=""
        values=[]
        result={}
        print("get_available Here 1")
        try:
            user_id=self.get_manzada_user_id(fb_id)
            # Prepare the connection to the server
            odoo = odoorpc.ODOO('app.manzada.net', port=8069)
            odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
            print("get_available HERE 2")
            print("get_available PROD IDS : "+str(product_ids))
            if 'product.product' in odoo.env:
                product_product = odoo.env['product.product']
                print("get_available HERE 3")
                products = product_product.search([('id', 'in', product_ids),('virtual_available', '>=',1)])
                print("get_available Here 4")
                if products:
                    print("Get_available Here 5")
                    count=0
                    for product in product_product.browse(products):
                        count+=1
                        product_id=product.id
                        qty_available=product.qty_available
                        virtual_available=product.virtual_available
                        #values.append(product.name)
                        #values.append(qty_available)
                        #values.append(virtual_available)
                        #print(str(values))
                        result[product_id]=[product.name, qty_available, virtual_available]
                        #values.clear()
                else:
                    pass
            else:
                pass
        except:
            pass
        print(str(result))
        return result

    def get_warning_stok(self, response, value, fb_id, nama):
        text=""
        product_ids=[
                        1229,   #ACI 3 AS @25KG
                        1436,   #DANONE 600ML
                        1557,   #GULA PASIR MATAHARI 50KG 100
                        2242,   #LENCANA MERAH @25KG (naik) 50
                        2534,   #MASAKO AYAM (12x10x6) 11g  20
                        2535,   #MASAKO SAPI (12x10x6) 11g  10
                        2015,   #SARIMI AYAM BAWANG 1X40   100
                        2253,   #TERIGU SEGITIGA BIRU @25KG (naik)  50
                        2248,   #TEGU @25KG     150
                        3186    #TERIGU PAYUNG 25KG 100
                    ]
        product_min={
                        1229:150,   #ACI 3 AS @25KG
                        1436:50,    #DANONE 600ML
                        1557:100,   #GULA PASIR MATAHARI 50KG 100
                        2242:50,    #LENCANA MERAH @25KG (naik) 50
                        2534:20,    #MASAKO AYAM (12x10x6) 11g  20
                        2535:10,    #MASAKO SAPI (12x10x6) 11g  10
                        2015:100,   #SARIMI AYAM BAWANG 1X40   100
                        2253:50,    #TERIGU SEGITIGA BIRU @25KG (naik)  50
                        2248:150,   #TEGU @25KG     150
                        3186:100    #TERIGU PAYUNG 25KG 100
                    }
        warning_items={}
        print("get_warning_stok Here 1")
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_warning_stok HERE 2")
                if 'product.product' in odoo.env:
                    product_product = odoo.env['product.product']
                    print("get_warning_stok HERE 3")
                    products = product_product.search([('id', 'in', product_ids)])
                    print("get_warning_stok Here 4")
                    if products:
                        print("get_warning_stok Here 5")
                        for product in product_product.browse(products):
                            product_id=product.id
                            qty_available=product.qty_available
                            virtual_available=product.virtual_available
                            if virtual_available<=product_min[product_id]:
                                text="STOCK WARNING :\n"
                                warning_items[product_id]=[product.name, qty_available, virtual_available]
                        print("get_warning_stok Here 6")
                        for key, values in warning_items.items():
                            product_name=values[0]
                            qty_available=values[1]
                            virtual_available=values[2]
                            text=text+"""
{}
Stok Fisik : {}
Stok Perkiraan : {}
""".format(product_name, locale.format("%d", qty_available, 1), locale.format("%d", virtual_available, 1))
                        print("get_warning_stok Here 7")
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except:
            pass
        print(text)
        return text

    def get_available_stok_old(self, response, value, fb_id, nama, product_ids, id_toko):
        text=""
        result=[]
        print("get_available Here 1")
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                user_id=self.get_manzada_user_id(fb_id)
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_available HERE 2")
                print("get_available PROD IDS : "+str(product_ids))
                if 'product.product' in odoo.env:
                    product_product = odoo.env['product.product']
                    print("get_available HERE 3")
                    products = product_product.search([('id', 'in', product_ids),('virtual_available', '>=',1)])
                    print("get_available Here 4")
                    if products:
                        print("Get_available Here 5")
                        count=0
                        for product in product_product.browse(products):
                            count+=1
                            record_history=self.sql_query(sql_product_sale_history_sum.format(user_id, id_toko, product.id))
                            for row in record_history:
                                minimal=int(row[1])+(int(row[1])*(20/100))
                            record_progress=self.sql_query(sql_progress_sale.format(user_id, id_toko, product.id))
                            for row in record_progress:
                                progress=row[1]
                            #print("Here 6")
                            nama_produk=product.name
                            #print("Here 7")
                            qty_available=product.qty_available
                            #print("Here 8")
                            virtual_available=product.virtual_available
                            #print("Here 9")
                            #rma_available=product.rma_available
                            #print("Here 10")
                            #rma_virtual_available=product.rma_virtual_available
                            print("Here 11")
                            text="""
{}
Stok Perkiraan  : {}
Minimal order   : {}
Progress        : {}""".format(nama_produk, locale.format("%d", qty_available, 1), locale.format("%d", virtual_available, 1), locale.format("%d", minimal,1), locale.format("%d", progress, 1))
                            result.append(text)
                            text=""
                            print("Here 12")
                    else:
                        text="{}. Maaf Rin tidak bisa menemukan produk available".format(nama)
                        result.append(text)
            else:
                text=self.get_server_exception("ambil_data", nama)
                result.append(text)
        except:
            print("Ada soket error : " + sys.exc_info()[0])
            text="Gagal memproses data, silahkan dicoba lagi.."
            result.append(text)
        return result

    def get_draft(self, value, fb_id, nama):
        text=""
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_draft HERE 2")
                if 'account.invoice' in odoo.env:
                    current_date = datetime.date.today()
                    user_id=self.get_manzada_user_id(fb_id)
                    account_invoice = odoo.env['account.invoice']
                    print("get_draft HERE 3")
                    invoice_ids = account_invoice.search([('state', '=', 'draft'),('user_id', '=', user_id), ('type', '=', 'out_invoice')]) #('date_invoice','=', str(current_date))])
                    print("get_draft Here 4")
                    grand_total=0
                    if invoice_ids:
                        for invoice in account_invoice.browse(invoice_ids):
                            toko=invoice.partner_id.name
                            tgl=invoice.date_invoice
                            amount_total=invoice.amount_total
                            grand_total+=amount_total
                            text=text+"""
{}
{}
Total : {}""".format(toko, str(tgl), locale.format("%d", amount_total, 1)) + '\n'
                        text=text+"\nGrand Total : {}".format(locale.format("%d", grand_total, 1))
                    else:
                        check_so=self.get_so(value, fb_id, nama)
                        check_validasi=self.get_open(value, fb_id, nama)
                        if check_so:
                            text="{}. Maaf seluruh orderan kamu hari ini belum melalui/masih proses tahapan loading(muat)".format(nama)
                        else:
                            if check_validasi:
                                text="{}. faktur kamu hari ini semuanya sudah divalidasi :)"
                            else:
                                text="{}. Maaf Rin tidak menemukan draft faktur untuk saat ini".format(nama)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_open(self, value, fb_id, nama):
        text=""
        result=False
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_open HERE 2")
                if 'account.invoice' in odoo.env:
                    current_date = datetime.date.today()
                    user_id=self.get_manzada_user_id(fb_id)
                    account_invoice = odoo.env['account.invoice']
                    print("get_open HERE 3")
                    invoice_ids = account_invoice.search([('state', 'in', ['open','paid']),('user_id', '=', user_id),('date_invoice','=', str(current_date))])
                    print("get_open HERE 4")
                    if invoice_ids:
                        for invoice in account_invoice.browse(invoice_ids):
                            toko=invoice.partner_id.name
                            amount_total=invoice.amount_total
                            text=text+"""
{}
Total   : {}""".format(toko, locale.format("%d", amount_total, 1)) + '\n'
                        result=True
                    else:
                        result=False
            else:
                text=self.get_server_exception("ambil_data", nama)
                result=False
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
            result=False
        return result

    def get_so(self, value, fb_id, nama):
        text=""
        result=False
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_so HERE 2")
                if 'sale.order' in odoo.env:
                    current_date = datetime.date.today()
                    use_id=self.get_manzada_user_id(fb_id)
                    sale_order = odoo.env['sale.order']
                    print("get_so HERE 3")
                    sale_order_ids = sale_order.search([('state', 'in', ['draft','progress']),('user_id', '=', user_id),('date_order','>=', str(current_date) + ' 00:00:00')])
                    print("get_so HERE 4")
                    if sale_order_ids:
                        for order in sale_order.browse(sale_order_ids):
                            toko=order.partner_id.name
                            tgl=order.date_order
                            amount_total=order.amount_total
                            text=text+"""
{}
Total   : {}""".format(toko, locale.format("%d", amount_total, 1)) + '\n'
                        result=True
                    else:
                        result=False
            else:
                text=self.get_server_exception("ambil_data", nama)
                result=False
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
            result=False
        return result

    def get_faktur_pajak(self, response, value, fb_id, nama):
        result=[]
        product_ids=[]
        if '_text' in response:
            body=response['_text'].split()
        print("BKP 1 LEN : " + str(len(body)))
        if len(body) == 6 :
            toko=body[5]
            try:
                if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                    current_date = datetime.date.today()
                    str_first_date=str(current_date.year)+' '+str(current_date.month)+' 01'
                    a_three_month = relativedelta(months=3)
                    a_last_month = relativedelta(months=1)
                    first_date=datetime.datetime.strptime(str_first_date, '%Y %m %d')
                    first_three_month = first_date - a_three_month
                    first_last_month = first_date - a_last_month
                    #last_month_date=datetime.date(first_last_month.year + (first_last_month.month == 12),
                    #(first_last_month.month + 1 if first_last_month.month < 12 else 1), 1) - datetime.timedelta(1)
                    #begin_date=str(first_three_month.year)+' '+str(first_three_month.month)+' 01'
                    #last_date_month = datetime.date(first_last_month.year + (first_last_month.month == 12),
                    #    (first_last_month.month + 1 if first_last_month.month < 12 else 1), 1) - datetime.timedelta(1)
                    last_date_month=datetime.date(current_date.year + current_date.month // 12,
                            current_date.month % 12 + 1, 1) - datetime.timedelta(1)
                    begin_date=str_first_date
                    end_date=str(last_date_month.strftime('%Y %m %d'))
                    print("BEGIN DATE : " + begin_date)
                    print("END DATE : " + end_date)
                    user_id=self.get_manzada_user_id(fb_id) #'3364431640310686')
                    record=self.sql_query(sql_get_partner_id.format(toko))
                    if record:
                        for row in record:
                            id_toko=int(row[0])
                        print("ID Toko :" + str(id_toko))
                        print("USER ID :" + str(user_id))
                        if fb_id=='3432901240109402':
                            record_products=self.sql_query(sql_product_sale_bkp_boss.format(id_toko, begin_date, end_date))
                        else:
                            text="Maaf... lokasi Anda tidak sesuai/tidak terdaftar pada GeoIP public cloud server"
                            result.append(text)
                        if record_products:
                            print("BKP Here 2")
                            total_setor=0
                            for row in record_products:
                                print("BKP Here 3")
                                nama_barang=row[1]
                                kts=row[2]
                                subtotal=row[3]
                                if row[4]:
                                    modal=kts*row[4]
                                    margin=int(subtotal)-int(modal)
                                    keluar=int(subtotal)*(10/100)
                                    masuk=int(modal)*(10/100)
                                    kb=keluar-masuk
                                    total_setor=total_setor+kb
                                else:
                                    modal=0
                                text="""
{}
Kuantitas : {}
Total Value : {}
Modal : {}
Margin : {}
*Simulasi setor, asumsi jika ada nilai kredit masukan :
Kurang bayar (setor ke negara) : {}
""".format(nama_barang, locale.format("%d", kts, 1), locale.format("%d", subtotal, 1), locale.format("%d", modal, 1), locale.format("%d", margin, 1), locale.format("%d", kb, 1))
                                #print("BKPHere 4")
                                result.append(text)
                                text=""
                            print("BKP Here 4")
                            result.append("Total Setor Ke Negara : {}".format(locale.format("%d", total_setor, 1)))
                        else:
                            if fb_id=='3432901240109402':
                                text="Maaf, Rin tidak bisa menemukan penjualan BKP untuk toko yang anda input."
                                result.append(text)
                    else:
                        text="""
Maaf Rin tidak bisa menemukan nama toko yang mirip dengan {}
Silahkan periksa kembali penulisan nama toko
Harap diketahui, satu huruf atau spasi pun juga berpengaruh""".format(toko)
                        result.append(text)
                else:
                    text=self.get_server_exception("ambil_data", nama)
                    result.append(text)
            except:
                print("Ada soket error : " + sys.exc_info()[0])
                text="Gagal memproses data, silahkan dicoba lagi.."
                result.append(text)
        else:
            text="Maaf lokasi Anda tidak sesuai/tidak terdaftar pada GeoIP public cloud server?"
            result.append(text)
        return result

    def get_omzet(self, fb_id, nama):
        current_date = datetime.date.today()
        last_date=datetime.date(current_date.year + (current_date.month == 12), 
                (current_date.month + 1 if current_date.month < 12 else 1), 1) - datetime.timedelta(1)
        begin_date=str(current_date.year)+' '+str(current_date.month)+' 01'
        end_date=str(current_date.year)+' '+str(current_date.month)+' '+str(last_date)
        text=""
        user_id=self.get_manzada_user_id(fb_id)
        target_sales={
                5:3427200000,
                31:2632000000, #2050000000,
                7:1904000000, #1500000000,
                9:2260000000, #1500000000,
                44:1288000000, #1050000000,
                6:1288000000,
                56:1880800000}
        sales={
                5:"Zulkarnaen",
                31:"Ahmad Syarifudin",
                7:"Tedi Guntara",
                9:"Agus Ahmad Rian",
                44:"Agung Aprianto",
                56:"Adi",
                6:"Edi"}
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_omzet)
                if record:
                    total_omzet = 0
                    grand_total = 0
                    persentase = None
                    rank=0
                    for row in record:
                        crown=""
                        rank+=1
                        if rank == 1:
                            crown = "👑"
                        user_id=row[0]
                        if row[1]:
                            total_omzet=row[1]
                        else:
                            total_omzet=0
                        grand_total+=total_omzet
                        if row[2]:
                            persentase=row[2]
                        else:
                            persentase=0
                        #text = text + "\n\n" + sales[user_id] + " " + crown + "\n" + locale.format("%d",total_omzet,1) + "\t" + str(persentase) + "%"
                        text = text + "\n\n" + sales[user_id] + " " + crown + "\n" + self.ribuan(total_omzet) + "\t" + str(persentase) + "%"
                    #text=text + '\n\nGrand Total : ' + locale.format("%d", grand_total, 1)
                    text=text + '\n\nGrand Total : ' + self.ribuan(grand_total)
                else:
                    text="Maaf. Rin tidak bisa menemukan data omzet untuk saat ini."
            else:
                text=self.get_server_exception("ambil_data", nama)
        except Exception as e:
            text="Gagal memproses data, silahkan dicoba lagi.. {}".format(str(e))
        return text
        
    def get_omzet_harian(self, o):
        text=""
        if o:
           user_id=5
        if o=='agus':
            user_id=9
        if o=='ahmad':
            user_id=31
        if o=='tedi':
            user_id=7
        if o=='agung':
            user_id=44
        if o=='adi':
            user_id=56
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_omzet_harian.format(user_id))
                if record:
                    total_omzet=0
                    for row in record:
                        if row[0]:
                            total_omzet=row[0]
                    text = locale.format("%d",total_omzet,1)
                else:
                    text="Maaf. Rin tidak menemukan data omzet [{}] untuk saat ini.".format(o)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_omzet_by_date(self, fb_id, nama, tgl_min, tgl_max):
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_omzet_by_date.format(tgl_min, tgl_max))
                if record:
                    total_omzet=0
                    for row in record:
                        if row[0]:
                            total_omzet=row[0]
                    text = locale.format("%d",total_omzet,1)
                else:
                    text="Maaf. Rin tidak menemukan data omzet [{}] untuk saat ini.".format(o)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_omzet_by_date_detail(self, fb_id, nama, tgl_min, tgl_max):
        current_date = datetime.date.today()
        last_date=datetime.date(current_date.year + (current_date.month == 12), 
                (current_date.month + 1 if current_date.month < 12 else 1), 1) - datetime.timedelta(1)
        begin_date=str(current_date.year)+' '+str(current_date.month)+' 01'
        end_date=str(current_date.year)+' '+str(current_date.month)+' '+str(last_date)
        text=""
        user_id=self.get_manzada_user_id(fb_id)
        target_sales={
                5:3427200000,
                31:2632000000, #2050000000,
                7:1904000000, #1500000000,
                9:2260000000, #1500000000,
                44:1288000000, #1050000000,
                6:1288000000,
                56:1880800000}
        sales={
                5:"Zulkarnaen",
                31:"Ahmad Syarifudin",
                7:"Tedi Guntara",
                9:"Agus Ahmad Rian",
                44:"Agung Aprianto",
                56:"Adi",
                6:"Edi"}
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_omzet_by_date_detail.format(tgl_min, tgl_max))
                if record:
                    total_omzet = 0
                    grand_total = 0
                    persentase = None
                    rank=0
                    for row in record:
                        crown=""
                        rank+=1
                        if rank == 1:
                            crown = "👑"
                        user_id=row[0]
                        if row[1]:
                            total_omzet=row[1]
                        else:
                            total_omzet=0
                        grand_total+=total_omzet
                        if row[2]:
                            persentase=row[2]
                        else:
                            persentase=0
                        #text = text + "\n\n" + sales[user_id] + " " + crown + "\n" + locale.format("%d",total_omzet,1) + "\t" + str(persentase) + "%"
                        text = text + "\n\n" + sales[user_id] + " " + crown + "\n" + self.ribuan(total_omzet) + "\t" + str(persentase) + "%"
                    #text=text + '\n\nGrand Total : ' + locale.format("%d", grand_total, 1)
                    text=text + '\n\nGrand Total : ' + self.ribuan(grand_total)
                else:
                    text="Maaf. Rin tidak bisa menemukan data omzet untuk saat ini."
            else:
                text=self.get_server_exception("ambil_data", nama)
        except Exception as e:
            text="Gagal memproses data, silahkan dicoba lagi.. {}".format(str(e))
        return text


    def get_pembelian_by_date(self, fb_id, nama, tgl_min, tgl_max):
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_pembelian_by_date.format(tgl_min, tgl_max))
                if record:
                    total_pembelian=0
                    for row in record:
                        if row[0]:
                            total_pembelian=row[0]
                    text = locale.format("%d",total_pembelian,1)
                else:
                    text="Maaf. Rin tidak menemukan data pembelian [{}] untuk saat ini.".format(o)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_residual(self, fb_id):
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_residual)
                if record:
                    total_piutang=0
                    for row in record:
                        if row[0]:
                            total_piutang=row[0]
                    text = locale.format("%d",total_piutang,1)
                else:
                    text="Maaf. Rin tidak menemukan data Piutang [{}] untuk saat ini.".format(o)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_hutang(self, fb_id):
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                record=self.sql_query(sql_hutang)
                if record:
                    total_hutang=0
                    for row in record:
                        if row[0]:
                            total_hutang=row[0]
                    text = locale.format("%d",total_hutang,1)
                else:
                    text="Maaf. Rin tidak menemukan data Hutang [{}] untuk saat ini.".format(o)
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_product_sales(self, fb_id, nama, produk, tgl_min, tgl_max, sales=None):
        traperX=""
        text=""
        if sales=='zul':
           user_id=5
        if sales=='agus':
            user_id=9
        if sales=='ahmad':
            user_id=31
        if sales=='tedi':
            user_id=7
        if sales=='agung':
            user_id=44
        if sales=='adi':
            user_id=56
        if sales=='edi':
            user_id=6
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                result=[]
                if sales:
                    record=self.sql_query(sql_product_sales_salesman.format(produk, tgl_min, tgl_max, user_id))
                else:
                    record=self.sql_query(sql_product_sales.format(produk, tgl_min, tgl_max))
                if record:
                    total_omzet=0
                    for row in record:
                        nama_barang=row[0]
                        total_sales=row[1]
                        text=text+"{}\t : {}".format(nama_barang, locale.format("%d", total_sales, 1))
                        result.append(text)
                        text=""
                else:
                    result.append("Nihil")
            else:
                result.append(self.get_server_exception("ambil_data", nama))
        except:
            result.append("Gagal memproses data, silahkan dicoba lagi..")
        return result

    def get_insentif(self, fb_id, nama, param=None):
        text=""
        if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            record=self.sql_query(sql_insentif_salesman.format(self.get_manzada_user_id(fb_id)))
            result=[]
            if record:
                produk = None
                terjual = 0
                persen = 0
                insentif = 0
                total_insentif = 0
                for row in record:
                    produk=row[0]
                    terjual=row[1]
                    persen=row[2]
                    insentif=row[3]
                    total_insentif += insentif
                    text=text+"""
{}
Terjual     : {}
Pencapaian  : {}%
Insentif    : {}""".format(produk, locale.format("%d", terjual, 1), locale.format("%d", persen, 1), locale.format("%d", insentif, 1))
                    result.append(text)
                    text=""
                if len(result) > 0:
                    result.append('\n-------------------------')
                    result.append("Total Insentif Produk : " + locale.format("%d", total_insentif, 1))
            else:
                result.append("Maaf {}. Rin belum mendaftarkan id FB kamu pada laporan insentif.".format(nama))
        else:
            result.append(self.get_server_exception("ambil_data", nama))
        return result

    def get_insentif_by_date(self, fb_id, nama, tgl_min, tgl_max, sales=None):
        text=""
        if sales=='zul':
           user_id=5
        if sales=='agus':
            user_id=9
        if sales=='ahmad':
            user_id=31
        if sales=='tedi':
            user_id=7
        if sales=='agung':
            user_id=44
        if sales=='adi':
            user_id=56
        if sales=='edi':
            user_id=6
        if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            record=self.sql_query(sql_insentif_salesman_by_date.format(user_id, tgl_min, tgl_max))
            result=[]
            if record:
                produk = None
                terjual = 0
                persen = 0
                insentif = 0
                total_insentif = 0
                for row in record:
                    produk=row[0]
                    terjual=row[1]
                    persen=row[2]
                    insentif=row[3]
                    total_insentif += insentif
                    text_o=text+"""
{}
Terjual     : {}
Pencapaian  : {}%
Insentif    : {}""".format(produk, locale.format("%d", terjual, 1), locale.format("%d", persen, 1), locale.format("%d", insentif, 1))
                    #result.append(text)
                    text=text+"""
{}
Terjual     : {}
Pencapaian  : {}%
Insentif    : {}""".format(produk, self.ribuan(terjual), locale.format("%d", persen, 1), self.ribuan(insentif))
                    result.append(text)
                    text=""
                if len(result) > 0:
                    result.append('\n-------------------------')
                    #result.append("Total Insentif Produk : " + locale.format("%d", total_insentif, 1))
                    result.append("Total Insentif Produk : " + self.ribuan(total_insentif))
            else:
                result.append("Maaf {}. Rin belum mendaftarkan id FB kamu pada laporan insentif.".format(nama))
        else:
            result.append(self.get_server_exception("ambil_data", nama))
        return result

    def get_insentif_pengirim(self, fb_id, nama, param=None):
        text=""
        if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            record = None
            record_terigu = None
            record_gula = None
            if param=='terigu':
                record=self.sql_query(sql_insentif_terigu)
            if param=='gula':
                record=self.sql_query(sql_insentif_gula)
            if param=='pengirim':
                record_terigu=self.sql_query(sql_insentif_terigu)
                record_gula=self.sql_query(sql_insentif_gula)
            result=[]
            if record and (param=='gula' or param=='terigu'):
                nama = None
                insentif = 0
                total_insentif = 0
                for row in record:
                    nama=row[0]
                    insentif=row[1]
                    total_insentif += insentif
                    text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                    result.append(text)
                    text=""
                if len(result) > 0:
                    result.append('\n-------------------------')
                    result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
            elif param=='pengirim':
                nama=None
                insentif=0
                total_insentif=0
                if record_terigu and not record_gula:
                    for row in record_terigu:
                        nama=row[0]
                        insentif=row[1]
                        total_insentif += insentif
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
                if record_gula and not record_terigu:
                    for row in record_gula:
                        nama=row[0]
                        insentif=row[1]
                        total_insentif += insentif
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
                if record_terigu and record_gula:
                    for row in record_terigu:
                        print("IM HERE KONSOLIDASI PENGIRIM")
                        nama=row[0]
                        insentif=row[1]
                        for row2 in record_gula:
                            if nama==row2[0]:
                                insentif += row2[1]
                        total_insentif += insentif
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
            else:
                result.append("Maaf {}. Rin belum mendaftarkan id FB kamu pada laporan insentif.".format(nama))
        else:
            result.append(self.get_server_exception("ambil_data", nama))
        return result

    def get_insentif_pengirim_by_date(self, fb_id, nama, tgl_min, tgl_max, param=None):
        text=""
        if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            record = None
            record_terigu = None
            record_gula = None
            if param=='terigu':
                record=self.sql_query(sql_insentif_terigu_by_date.format(tgl_min, tgl_max))
            if param=='gula':
                record=self.sql_query(sql_insentif_gula_by_date.format(tgl_min, tgl_max))
            if param=='pengirim':
                record_terigu=self.sql_query(sql_insentif_terigu_by_date.format(tgl_min, tgl_max))
                record_gula=self.sql_query(sql_insentif_gula_by_date.format(tgl_min, tgl_max))
            result=[]
            if record and (param=='gula' or param=='terigu'):
                nama = None
                insentif = 0
                total_insentif = 0
                for row in record:
                    nama=row[0]
                    insentif=row[1]
                    total_insentif += insentif
                    text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                    result.append(text)
                    text=""
                if len(result) > 0:
                    result.append('\n-------------------------')
                    result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
            elif param=='pengirim':
                nama=None
                insentif=0
                total_insentif=0
                if record_terigu and not record_gula:
                    for row in record_terigu:
                        nama=row[0]
                        insentif=row[1]
                        total_insentif += insentif
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
                if record_gula and not record_terigu:
                    for row in record_gula:
                        nama=row[0]
                        insentif=row[1]
                        total_insentif += insentif
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
                if record_terigu and record_gula:
                    for row in record_terigu:
                        print("IM HERE KONSOLIDASI PENGIRIM")
                        nama=row[0]
                        insentif=row[1]
                        for row2 in record_gula:
                            if nama==row2[0]:
                                insentif += row2[1]
                        total_insentif += insentif
                        if "Aji" in nama:
                            nama="Zian"
                        elif "Daryat" in nama:
                            nama="Riki Galih"
                        elif "Gugun" in nama:
                            nama="Albet"
                        elif "Jaka" in nama:
                            nama="Endang"
                        elif "Saepul" in nama:
                            nama="Markun"
                        elif "Sarman" in nama:
                            nama="Cucu"
                        elif "Suhir" in nama:
                            nama="Rian"
                        elif "Tatang" in nama:
                            nama="Rendi Hanapi"
                        if "Top Office" in nama:
                            nama="Mahfud"
                        text=text+"{}\t : {}".format(nama, locale.format("%d", insentif, 1))
                        result.append(text)
                        text=""
                    if len(result) > 0:
                        result.append('\n-------------------------')
                        result.append("Total Insentif {} : ".format(param) + locale.format("%d", total_insentif, 1))
            else:
                result.append("Maaf {}. Rin belum mendaftarkan id FB kamu pada laporan insentif.".format(nama))
        else:
            result.append(self.get_server_exception("ambil_data", nama))
        return result

    def get_insentif_faktur(self, value, fb_id, nama):
        text=""
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_insentif_faktur HERE 2")
                if 'account.invoice' in odoo.env:
                    current_date = datetime.date.today()
                    last_date=datetime.date(current_date.year + (current_date.month == 12),(current_date.month + 1 if current_date.month < 12 else 1), 1) - datetime.timedelta(1)
                    begin_date=str(current_date.year)+' '+str(current_date.month)+' 01'
                    end_date=str(last_date).replace('-',' ')
                    #begin_date='2022-11-01'
                    #end_date='2022-11-31'
                    print(begin_date)
                    print(end_date)
                    user_id=self.get_manzada_user_id(fb_id)
                    account_invoice = odoo.env['account.invoice']
                    invoice_ids=account_invoice.search([('type','=','out_invoice'),('state','in',['open','paid']),('user_id','=',user_id),('date_invoice','>=',begin_date),('date_invoice','<=',end_date)])
                    if invoice_ids:
                        count=0
                        insentif=0
                        for invoice in account_invoice.browse(invoice_ids):
                            count+=1
                            insentif=500*count
                        text="""
Total Faktur    : {}
Total Insentif  : {}""".format(locale.format("%d", count, 1), locale.format("%d", insentif,1))
                        print("get_insentif_faktur SUCCESS")
                    else:
                        text="Maaf, Rin tidak bisa menemukan list faktur kamu."
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_insentif_faktur_by_date(self, value, fb_id, nama, tgl_min, tgl_max, sales=None):
        text=""
        try:
            if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                text=""
                if sales=='zul':
                    user_id=5
                if sales=='agus':
                    user_id=9
                if sales=='ahmad':
                    user_id=31
                if sales=='tedi':
                    user_id=7
                if sales=='agung':
                    user_id=44
                if sales=='adi':
                    user_id=56
                if sales=='edi':
                    user_id=6
                # Prepare the connection to the server
                odoo = odoorpc.ODOO('app.manzada.net', port=8069)
                # Login
                odoo.login('manzada', 'rin@manzada.net', 'EnakBangetKalian')
                print("get_insentif_faktur HERE 2")
                if 'account.invoice' in odoo.env:
                    current_date = datetime.date.today()
                    last_date=datetime.date(current_date.year + (current_date.month == 12),(current_date.month + 1 if current_date.month < 12 else 1), 1) - datetime.timedelta(1)
                    begin_date=tgl_min
                    end_date=tgl_max
                    print(begin_date)
                    print(end_date)
                    account_invoice = odoo.env['account.invoice']
                    invoice_ids=account_invoice.search([('type','=','out_invoice'),('state','in',['open','paid']),('user_id','=',user_id),('date_invoice','>=',begin_date),('date_invoice','<=',end_date)])
                    if invoice_ids:
                        count=0
                        insentif=0
                        for invoice in account_invoice.browse(invoice_ids):
                            count+=1
                            insentif=500*count
                        text_o="""
Total Faktur    : {}
Total Insentif  : {}""".format(locale.format("%d", count, 1), self.ribuan(insentif))
                        print("get_insentif_faktur SUCCESS")
                        text="""
Total Faktur    : {}
Total Insentif  : {}""".format(locale.format("%d", count, 1), self.ribuan(insentif))
                        print("get_insentif_faktur SUCCESS")
                    else:
                        text="Maaf, Rin tidak bisa menemukan list faktur kamu."
            else:
                text=self.get_server_exception("ambil_data", nama)
        except:
            text="Gagal memproses data, silahkan dicoba lagi.."
        return text

    def get_stat_server(self, fb_id, nama):
        text=""
        if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
            resp_check=["Server [Online] :)", "Server [Online]. Tidak ada masalah di sisi server\
                        \nJika kesulitan membuka web\n1.Cek jaringan internet\n2.Kurangi beban memory HP\
                        \n3.Bersihkan cache chrome\n4.Off\On Mode pesawat\n5.Restart HP"]
            random.shuffle(resp_check)
            text=resp_check[0]
        else:
            text="Maaf {}. server sedang offline :(".format(nama)
        return text

    def get_cuaca(self, lokasi, fb_id, nama):
        text=""
        try:
            WEATHER_API_KEY = '878b26f74e49157a2a74101c716ed84f'
            BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
            URL = BASE_URL + "q=" + lokasi + "&appid=" + WEATHER_API_KEY
            # HTTP request
            response = requests.get(URL)
            # checking the status code of the request
            if response.status_code == 200:
                # getting data in the json format
                data = response.json()
                # getting the main dict block
                main = data['main']
                temperature = main['temp']
                humidity = main['humidity']
                pressure = main['pressure']
                report = data['weather']
                cuaca=report[0]['description']
                cuaca_dict={"broken clouds" : "berawan",
                        "scattered clouds" : "berawan",
                        "few clouds" : "sedikit berawan",
                        "overcast clouds" : "mendung",
                        "light rain" : "gerimis",
                        "moderate rain" : "hujan"}
                text="{}. Di {} {}, dengan suhu {}°celcius".format(nama, lokasi, cuaca_dict[cuaca], locale.format("%d", (temperature - 273.15),1))
                #text="""
                #{}
                #Suhu  : {}
                #Cuaca : {}""".format(lokasi, (temperature - 273.15), report[0]['description'])
                #print(f"{lokasi:-^30}")
                #print(f"Temperature: {temperature}")
                #print(f"Humidity: {humidity}")
                #print(f"Pressure: {pressure}")
                #print(f"Weather Report: {report[0]['description']}")
            else:
                text="mmmm... kasih tau nggak ya..."
        except:
            text="Sensor cuacanya lagi ada masalah.. sepertinya harus ngopi dulu :)"
        
        return text

    def get_commands(self, response, value, fb_id, nama):
        text=None
        body=[]
        if '_text' in response:
            body=response['_text'].split(' ')
        entities=response['entities']
        #object_type="object_type" in entities
        object_type=true
        user_id=self.get_manzada_user_id(fb_id)
        if value=="order":
            text=self.get_status_order(fb_id, nama)
        if value=="omzet":
            if len(body)==3 and (user_id==1 or nama=="Boss"):
                print("Cek Omzet By Date")
                tgl_min=body[1]
                tgl_max=body[2]
                text=self.get_omzet_by_date(fb_id, nama, tgl_min, tgl_max)
            if len(body)==4 and nama=="Boss":
                print("Cek Omzet By Date Detail")
                tgl_min=body[1]
                tgl_max=body[2]
                text=self.get_omzet_by_date_detail(fb_id, nama, tgl_min, tgl_max)
            if len(body)==1:
                print("Cek Omzet Normal")
                text=self.get_omzet(fb_id, nama)
                #if user_id==5 or nama=='Boss':
                #    if object_type:
                #        o=self.get_value(entities, "object_type")
                #        text=self.get_omzet_harian(o)
        if value=="residual":
            if user_id==1 or nama=="Boss":
                text=self.get_residual(fb_id)
        if value=="hutang":
            if user_id==1 or nama=="Boss":
                text=self.get_hutang(fb_id)
        if value=="pembelian":
            if len(body)==3 and (user_id==1 or nama=="Boss"):
                tgl_min=body[1]
                tgl_max=body[2]
                text=self.get_pembelian_by_date(fb_id, nama, tgl_min, tgl_max)
        if value=="insentif":
            text="Mau cek insentif apa?\nJika insentif produk silahkan ketik cek insentif produk\nJika Faktur silahkan ketik cek insentif faktur"
            if object_type:
                o=self.get_value(entities, "object_type")
                if o=="produk":
                    if len(body)==5 and nama=="Boss":
                        print("Insentif Produk By Date")
                        tgl_min=body[2]
                        tgl_max=body[3]
                        sales=body[4]
                        text=self.get_insentif_by_date(fb_id, nama, tgl_min, tgl_max, sales)
                    if len(body)<5:
                        text=self.get_insentif(fb_id, nama)
                if o=="faktur":
                    if len(body)==5 and nama=="Boss":
                        print("Insentif Faktur By Date")
                        tgl_min=body[2]
                        tgl_max=body[3]
                        sales=body[4]
                        text=self.get_insentif_faktur_by_date(value, fb_id, nama, tgl_min, tgl_max, sales)
                    if len(body)<5:
                        text=self.get_insentif_faktur(value, fb_id, nama)
                if o=="terigu" or o=="gula" or o=="pengirim":
                    if len(body)==4 and nama=="Boss":
                        tgl_min=body[2]
                        tgl_max=body[3]
                        text=self.get_insentif_pengirim_by_date(fb_id, nama, tgl_min, tgl_max, o)
                    if len(body)<4:
                        text=self.get_insentif_pengirim(fb_id, nama, o)
        if value=="out":
            if nama !='Boss':
                text="Data request ditolak oleh server."
                return text
            produk=""
            tgl_min=""
            tgl_max=""
            sales=""
            if len(body) == 5:
                #if fb_id != '3432901240109402' :
                #    text="User fb id belum dikenali..."
                #    return text
                produk=body[1]
                tgl_min=body[2]
                tgl_max=body[3]
                sales=body[4]
                text=self.get_product_sales(fb_id, nama, produk, tgl_min, tgl_max, sales)
            elif len(body) == 4:
                #if fb_id != '3432901240109402' :
                #    text="User fb id belum dikenali..."
                #    return text
                produk=body[1]
                tgl_min=body[2]
                tgl_max=body[3]
                text=self.get_product_sales(fb_id, nama, produk, tgl_min, tgl_max)
            else:
                text="Ada kesalahan format penulisan.. Periksa lagi perintah yang anda ketikan.."
        if value=="draft":
            text=self.get_draft(value, fb_id, nama)
        if value=="server":
            text=self.get_stat_server(fb_id, nama)
        if value=="stock":
            text=self.get_stok(response, value, fb_id, nama)
        if value=="rekomendasi":
            #if fb_id!=IAM:
            #    text="Saat ini kode rekomendasi lagi dimodifikasi dulu..\npada fase ini fitur dinonaktifkan untuk sementara, stay tune :)"
            #else:
            text=self.get_rekomendasi(response, value, fb_id, nama)
        if value=="abrakadabra":
            text=self.get_abrakadabra(response, value, fb_id, nama)
        if value=="faktur pajak":
            text=self.get_faktur_pajak(response, value, fb_id, nama)
        return text

    def analisa_kalimat(self, response, value, fb_id, nama):
        text=""
        rsp=[]
        entities=response['entities']
        subject='subject_type' in entities
        predikat='predikat_type' in entities
        kata_kerja='kata_kerja_type' in entities
        kata_sifat='kata_sifat_type' in entities
        kata_object='object_type' in entities
        bertanya='tanya_type' in entities
        informal='informal_type' in entities
        lokasi='lokasi_type' in entities
        cuaca='cuaca_type' in entities
        if bertanya:
            t=self.get_value(entities, 'tanya_type')
            if t=="gimana caranya":
                body=[]
                if '_text' in response:
                    body=response['_text'].split(' ', 2)
                if len(body) == 3:
                    rsp=["Kenapa {} pengen tau caranya {}".format(nama, body[2]), "Emmm.. Kasih tau nggak ya..?", "caranya coba menghadap kiblat lalu ucapkan takbir :)"]
                    random.shuffle(rsp)
            if t=="lagi apa":
                rsp=["lagi belajar :)", "lagi kerja", "lagi ngopi, {} udah ngopi?".format(nama), "lagi sibuk membalas pesan dari team sales :)"]
                random.shuffle(rsp)
            if t=="sehat?" or t=="gimana kabarnya":
                rsp=["Alhamdulillah :)", "Alhamdulillah, kamu?", "Alhamdulillah, sehat :)"]
                random.shuffle(rsp)
            if t=="masih lama":
                if self.check_server(SERVER, WEBPORT, TIMEOUT, RETRY):
                    rsp=["Server sudah online sekarang :)", "Udah online :)"]
                    random.shuffle(rsp)
                else:
                    rsp=["Maaf. Jika kendalanya seperti pemadaman oleh PLN, Kabel telkom yang putus, Rin belum bisa mengukur estimasi waktunya", "Sabar ya.., Rin berusaha yang terbaik"]
                    random.shuffle(rsp)
        if cuaca:
            text=""
            c=self.get_value(entities, 'cuaca_type')
            text="{} dimana ya?".format(c)
            if lokasi:
                l=self.get_value(entities, 'lokasi_type')
                #if c !="cuaca":
                #    text="Sebentar Rin coba cari info di {} {} atau nggak".format(l, c)
                #else:    
                #    text="Sebentar Rin Coba cari info di {} {}nya gimana..".format(l, c)
                if l=="disitu":
                    lokasi="Cisalak"
                if l=="disini":
                    l="unknown"
                    text="Yang bener {}?".format(nama)
                if l != "unknown":
                    text=self.get_cuaca(l, fb_id, nama)
            return text
                    
        if predikat:
            p=self.get_value(entities, 'predikat_type')
            if p=="mau":
                rsp=["Boleh :)", "{} mau apa?".format(nama)]
                random.shuffle(rsp)
        if kata_kerja:
            kk=self.get_value(entities, 'kata_kerja_type')
            rsp=["{} apa {}?".format(kk, nama), "{} ?".format(kk), "nanti aja {}nya".format(kk), "silahkan {}".format(kk)]
            random.shuffle(rsp)
        if predikat and kata_kerja:
            p=self.get_value(entities, 'predikat_type')
            kk=self.get_value(entities, 'kata_kerja_type')
            if subject:
                s=self.get_value(entities, 'subject_type')
                if s == "kamu":
                    s="Rin"
                if s=="saya":
                    s=nama
                if s=="Rin":
                    rsp=["Rin {} {} :)".format(p, kk), "belum", "nanti"]
                    random.shuffle(rsp)
                if s==nama:
                    rsp=["Mangga {} :)".format(nama), "silahkan {} :)".format(nama), "Ok {} :)".format(nama)]
                    if p=="belum":
                        rsp=["kenapa {} {} {}?".format(s, p, kk), "masa sih?", "kenapa ?", "apa efeknya jika kamu {} {}?".format(p, kk)]
                    if p=="udah":
                        rsp=["good", "mantap", "apa efeknya jika kamu {} {}?".format(p, kk)]
                    random.shuffle(rsp)
            else:
                rsp=["Mangga {} :)".format(nama), "silahkan {} :)".format(nama), "Ok {} :)".format(nama), "{} {} apa?".format(p, kk)]
                if p=="udah" or p=="belum":
                    rsp=["Belum {} :(".format(kk), "Udah :)", "nanti", "Udah {}, kamu?".format(kk)]
                random.shuffle(rsp)
        if predikat and kata_object:
            p=self.get_value(entities, 'predikat_type')
            o=self.get_value(entities, 'object_type')
            if p=="mau":
                rsp=["Boleh :)", "{} mau apa?".format(nama), "kenapa kamu mau {}?".format(o), "untuk apa?", "nanti saja", "jangan"]
                random.shuffle(rsp)
        
        if len(rsp) > 0:
            text=rsp[0]
        return text

    def get_value(self, entities, entity):
        return entities[entity][0]['value']


    def get_server_exception(self, tipe, nama):
        text=""
        if tipe=="ambil_data":
            resp=["Maaf {}. 🙏🏻 untuk saat ini Rin tidak bisa mengambil data dikarenakan ada gangguan koneksi ke server ",
                    "Maaf {}. untuk saat ini tidak bisa memproses data. 🙏🏻",
                    "{}. Terjadi gangguan disaat proses. silahkan coba lagi nanti",
                    "Tidak bisa memproses data sekarang :(, silahkan dicoba lagi nanti {}.",
                    "{}. Data tidak bisa diproses, masih ada kendala jaringan 🙏🏻"]
            random.shuffle(resp)
            text=resp[0].format(nama)
        return text

    def get_manzada_user_id(self, fb_id):
        user_id = 1
        if fb_id=='3264582853639869':
            user_id=9
        if fb_id=='3941390309222663':
            user_id=31
        if fb_id=='3724789247576364':#'3706874686003580':
            user_id=7
        if fb_id=='4937492586295334': #Agung
            user_id=44
        if fb_id=='4345408962193459':
            user_id=25
        if fb_id=="3364431640310686":
            user_id=5
        if fb_id=="4294487443937631":
            user_id=56
        if fb_id=="25176516441947351":
            user_id=6
        return user_id

    def is_int(self,s):
        result=False
        try:
            result=int(s)
        except ValueError:
            result = False
        return result

    def reformat(self, s, n):
        n_spasi=0
        spasi = ''
        if len(s) < n:
            n_spasi=n-len(s)
            spasi = ' ' * n_spasi
        return s+spasi

    def get_part_of_day(self, hour):
        return (
            "pagi" if 5 <= hour <= 11
            else
            "siang" if 12 <= hour <= 14
            else
            "sore" if 15 <= hour <= 17
            else
            "malam"
        )

    # assume value is a decimal
    def ribuan(self, value):
        str_value = str(value)+".00"
        separate_decimal = str_value.split(".")
        after_decimal = separate_decimal[0]
        before_decimal = separate_decimal[1]

        reverse = after_decimal[::-1]
        temp_reverse_value = ""

        for index, val in enumerate(reverse):
            if (index + 1) % 3 == 0 and index + 1 != len(reverse):
                temp_reverse_value = temp_reverse_value + val + "."
            else:
                temp_reverse_value = temp_reverse_value + val

        temp_result = temp_reverse_value[::-1]

        return temp_result + "," + before_decimal
