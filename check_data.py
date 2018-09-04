import RPi.GPIO as GPIO
import time
import smtplib
import sqlite3
import sys

gpio_port = 18;
log_file = '/home/pi/wasch/wasch2.log';
dbname = '/home/pi/wasch/wasch.db';
html_file = '/var/www/html/wasch.htm';
create_table = 'CREATE TABLE IF NOT EXISTS wasch (date text, led integer)';
select_table = 'SELECT * from wasch order by date DESC';
pattern = [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1];
email_user = 'user';
email_pass = 'pass';
email_from = '@from.com';
email_to   = ['email@to1.com', 'email@to2.com'];

GPIO.setmode(GPIO.BCM);
GPIO.setup(gpio_port, GPIO.IN);
GPIO_status = GPIO.input(gpio_port);
GPIO.cleanup();

def sendMail():
   subject = 'Waesche fertig!';

   headers = ["From: " + email_from,
           "Subject: " + subject,
           "To: " + email_to[0] + "," + email_to[1],
           "MIME-Version: 1.0",
           "Content-Type: text/html"];
   headers = "\r\n".join(headers);

   session = smtplib.SMTP('smtp.gmail.com', 587);

   session.ehlo();
   session.starttls();
   session.ehlo();
   session.login(email_user, email_pass) ;
   session.sendmail(email_from, email_to, headers + "\r\n\r\n" + time.strftime("%d.%m.%Y um %H:%M Uhr"));
   session.quit();
   return;

def startlog():
   f = open(log_file, 'w');
   f.write("erstellt " + time.strftime("%d.%m.%Y %H:%M:%S") + "\n");
   f.write("GPIO = " + str(gpio_port) + "\n");
   f.flush();
   f.close();
   return ;

def appendlog(logme):
   f = open(log_file, 'a');
   f.write(time.strftime("%d.%m.%Y %H:%M:%S : ") + logme + "\n");
   f.flush();
   f.close();
   return ;

def showdb():
  conn = sqlite3.connect(dbname, 20.0);
  cur = conn.cursor();
  cur.execute(select_table + " limit 180");

  rows = cur.fetchall()
  conn.close();

  appendlog("showdb START");

  for row in rows:
    appendlog("-> " + str(row[0]) + " - " + str(row[1]));

  appendlog("showdb ENDE");
  return;

def wipedb():
  appendlog("wipedb check");
  if len(sys.argv) > 1:
          appendlog("wipedb check, param: " + str(sys.argv[1]));
          if str(sys.argv[1]) == "wipe":
                  appendlog("wipedb wiping DB");
                  conn = sqlite3.connect(dbname, 20.0);
                  cur = conn.cursor();
                  cur.execute("DROP TABLE IF EXISTS wasch");
                  cur.execute(create_table);
                  conn.commit();
                  conn.close();

  return;

def insertdb():
  conn = sqlite3.connect(dbname, 20.0);
  cur = conn.cursor();
  cur.execute(create_table);
  cur.execute("INSERT INTO wasch VALUES (?, ?)", (time.strftime("%Y-%m-%d %H:%M:%S"), GPIO_status));
  conn.commit();
  conn.close();
  return;

def checkReset():
  hour = time.strftime("%H");
  result = hour == "03";
  appendlog("checkReset " + hour + " " + str(result));

  if result:
    wipedb();
    startlog();

  return;

def checkCompleted():
  conn = sqlite3.connect(dbname, 20.0);
  cur = conn.cursor();
  cur.execute(select_table + " limit 180");

  rows = cur.fetchall();
  conn.close();

  len_pattern = len(pattern);
  len_db = len(rows);
  if (len_db < len_pattern):
    appendlog("checkCompleted zu wenig DB Eintraege Pattern=" + str(len_pattern) + " DB=" + str(len_db));
    return False;

  for index in range(len_pattern):
    appendlog("checkCompleted checkPattern i=" + str(index) + " pattern=" + str(pattern[index]) + " db=" + str(rows[index][1]));
    if pattern[index] != rows[index][1]:
      appendlog("checkCompleted checkPattern diff bei i=" + str(index));
      return False;

  appendlog("checkCompleted checkPattern OK");

  return True;

def checkCompletedInLastHour():
  appendlog("checkCompletedInLastHour");
  conn = sqlite3.connect(dbname, 20.0);
  cur = conn.cursor();
  cur.execute(select_table + " limit 120");

  rows = cur.fetchall();
  conn.close();

  startswith0 = False;
  changedTo1 = False;
  ZeroCounter = 0;
  OneCounter = 0;

  if rows[0][1] == 0:
    startswith0 = True;

  for row in rows:
    if row[1] == 1:
      changedTo1 = True;
      OneCounter += 1;
    elif row[1] == 0:
      ZeroCounter += 1;

    if startswith0 and changedTo1 and OneCounter > 20 and ZeroCounter > 2:
      appendlog("checkCompletedInLastHour TRUE");
      return True;

  appendlog("checkCompletedInLastHour FALSE " + str(startswith0) + " " + str(changedTo1) + " " + str(OneCounter) + " " + str(ZeroCounter));
  return False;

def generateHtml():
  appendlog("generateHtml");
  f = open(html_file, 'w');
  f.write("<html>\n<head>\n<title>WaschberryPi</title>\n</head>\n");

  conn = sqlite3.connect(dbname, 20.0);
  cur = conn.cursor();
  cur.execute(select_table + " limit 300");

  rows = cur.fetchall()
  conn.close();

  f.write("<body>\n<p style=\"font-size:200%; text-align: center;\">\n");

  if GPIO_status:
    f.write(time.strftime("%Y-%m-%d %H:%M") + "<br>\n<b>Maschine l&auml;uft</b><br>\n");
    f.write("<img src=\"start.png\" width=\"300\" height=\"300\" border=\"0\" title=\"L&auml;uft\"><br>\n");
  else:
    f.write(time.strftime("%Y-%m-%d %H:%M") + "<br>\n<b>Maschine l&auml;uft nicht</b><br>\n");
    f.write("<img src=\"stop.png\" width=\"300\" height=\"300\" border=\"0\" title=\"L&auml;uft nicht\"><br>\n");

  if checkCompletedInLastHour():
    f.write("<br><b>Maschine ist fertig!</b><br>\n");

  f.write("<br><br><br>\n");

  for row in rows:
    if row[1] == 1:
      f.write(str(row[0]) + " - <img src=\"start_klein.png\" width=\"35\" height=\"35\" border=\"0\" align=\"top\"><br>\n");
    else:
      f.write(str(row[0]) + " - <img src=\"stop_klein.png\"  width=\"35\" height=\"35\" border=\"0\" align=\"top\"><br>\n");

  f.write("</p>\n</body>\n</html>");
  f.flush();
  f.close();
  return ;


appendlog("Start");
wipedb();
insertdb();
showdb();
generateHtml();

if checkCompleted():
  sendMail();

appendlog("Ende");
