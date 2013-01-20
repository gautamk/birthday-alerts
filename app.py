import datetime
import jinja2
import logging
import os
import webapp2
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.api import users
from random import random

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
TODO: Check for Optimizations
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class Reminders(db.Model):
    name            = db.StringProperty()
    emailId         = db.StringProperty()
    eventDay        = db.IntegerProperty()
    eventMonth      = db.IntegerProperty()
    eventYear       = db.IntegerProperty()
    
class Config(db.Model):
    sender_name     = db.StringProperty()
    sender_email    = db.StringProperty()
    appspot_id      = db.StringProperty()

class Messages(db.Model):
    messageId       = db.FloatProperty()
    message         = db.StringProperty(multiline=True)
    
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Reminder Handler:
    add / edit / delete reminders
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class ReminderHandler(webapp2.RequestHandler):
    def get(self):
        action = self.request.get('action')
        key = self.request.get('id')
        if action == 'delete':
            Reminders().get(key).delete()
            self.redirect('/')
        elif action == 'edit':
            self.response.out.write(renderTemplate('remainder.html', {'editEvent':getReminders(0,0,key), 'eventList':getReminders(), 'logoutUrl':users.CreateLogoutURL("/")}))
        else:
            self.response.out.write(renderTemplate('remainder.html', {'editEvent':'','eventList':getReminders(), 'logoutUrl':users.CreateLogoutURL("/")}))
    
    def post(self):
        key = self.request.get('id')
        if len(key) == 0:
            event = Reminders()
        else:
            event = Reminders().get(key)
        event.name = self.request.get('name')
        event.emailId = self.request.get('emailId')
        year, month, day = str(self.request.get('eventDate')).split('-')
        event.eventDay = int(day)
        event.eventMonth = int(month)
        event.eventYear = int(year)
        event.put()
        self.redirect('/')
        
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Message Handler:
    view/ add birthday wish messages
    TODO: Edit / Delete Messages 
    TODO: Rich Text Editor for Message Input
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class MessageHandler(webapp2.RequestHandler):
    def get(self):
        action = self.request.get('action')
        key = self.request.get('id')
        if action == 'delete':
            Messages().get(key).delete()
        else:
            messages = Messages().all() 
            if (messages.count() == 0):
                setupDefaultMessages()
            self.response.out.write(renderTemplate('messages.html',{'messages' : messages, 'logoutUrl':users.CreateLogoutURL("/")}))
    
    def post(self):
        logging.info('inserting message : %s' % (self.request.get('message')))
        message = Messages()
        message.messageId = random()
        message.message = self.request.get('message')
        message.put()
        self.redirect('/message')
        
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Configuration Handler:
    chnage sender email address, when birthday admin changes
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class ConfigurationHandler(webapp2.RequestHandler):
    def get(self):
        config = getConfig()
        if type(config) == type('str'):    
            sender_name = ''
            sender_email = ''
            appspot_id = ''
            key = ''
        else:
            sender_name = config.sender_name
            sender_email = config.sender_email
            appspot_id = config.appspot_id
            key = config.key()
        self.response.out.write(renderTemplate('config.html', {'sender_name':sender_name, 'sender_email':sender_email, 'appspot_id':appspot_id, 'id' : key, 'logoutUrl':users.CreateLogoutURL("/")}))
    
    def post(self):
        key = self.request.get('id')
        if len(key) == 0:
            config = Config()
        else:
            config = Config().get(self.request.get('id'))
        if config.sender_name == self.request.get('name') and config.sender_email == self.request.get('emailId') and config.appspot_id == self.request.get('appspotId'): 
            logging.info("Nothing to do. No change in name and email id and appspot_id")
        else:
            logging.info("saving configuration changes")
            config.sender_name = self.request.get('name')
            config.sender_email = self.request.get('emailId')
            config.appspot_id = self.request.get('appspotId')
            config.put()
        self.redirect('/config')
    
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Scheduler Handler:
    check and send out birthday wishes
    will be executed at 00:00 GMT, edit cron.yaml to customize
    TODO: A random Happy Birthday Song
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class SchedulerHandler(webapp2.RequestHandler):
    def get(self):
        reminders = getReminders(0,0)
        config = getConfig()
        for reminder in reminders:
            try:
                wish = getMessages()
                message = mail.EmailMessage(sender = config.sender_email, subject="Happy Birthday " + reminder.name)
                message.to = reminder.name + " <" + reminder.emailId + ">"
                message.body = "Happy Birthday" + wish
                message.html = renderTemplate('email.html',{'message' : wish, 'appspotId': config.appspot_id})
                logging.info(message.html)
                message.send()
                logging.info("Wishes sent for %s" % (reminder.name))
            except:
                logging.error('Error sending mail to  ' + reminder.name + " " + reminder.emailId)
    
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Functions:
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def getReminders(day=0, month=0, key=""):
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
        Use any integer other than zero for day & month 
        to get current day's events. 
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    logging.info("fetching reminder events")
    if key == "":
        Qry = Reminders.all()
        if (day !=0 and month != 0):
            Qry.filter("eventDay =", int(datetime.datetime.utcnow().strftime("%d")))
            Qry.filter("eventMonth =", int(datetime.datetime.utcnow().strftime("%m")))
        Qry.order("name")
        return Qry.run()
    else:
        return Reminders.get(key)

def getConfig():
    logging.info("reading configuration")
    Qry = Config.all()
    configs = Qry.run(limit=1)
    configuration=""
    for config in configs:
        configuration = config
    return configuration

def getMessages():
    logging.info("randomly picking a wish message")
    wishes = Messages.all().filter('messageId >=', random()).run(limit=1)
    if wishes is None:
        wishes = Messages.all().run(limit=1)
    message = ""
    for wish in wishes:
        message = wish.message
    return message
    
def renderTemplate(template, template_values):
    output = jinja_environment.get_template('templates/'+template)
    return output.render(template_values)

def setupDefaultMessages():
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
        http://www.1happybirthday.com
        TODO: Check if all selected messages are OK and CORRECT
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""    
    messages = []
    messages.append("Just when the caterpillar thinks that it is all grown up, it becomes a butterfly. \nHappy Birthday Butterfly.")
    messages.append("Celebrate your birthday today. Celebrate being Happy every day.")
    messages.append("May your birthday be filled with many happy hours and your life with many happy birthdays. \nHAPPY BIRTHDAY !!")
    messages.append("Well, you are another year older and you haven't changed a bit. \nThat's great because you are perfect just the way you are. \nHappy Birthday.")
    messages.append("Can you blow all those candles out or should we call the fire department? \nHappy Birthday.")
    messages.append("I hope this is the begining of your greatest, most wonderful year ever! \nHappy Birthday!!!")
    messages.append("Wishing you a day that is as special in every way as you are. \nHappy Birthday.")
    messages.append("You have to get older, but you don't have to grow up. \nHappy Birthday.")
    messages.append("Set the world on fire with your dreams and use the flame to light a birthday candle. \nHAPPY BIRTHDAY !!")
    messages.append("On this special day, \nI wish you all the very best, \nall the joy you can ever have \nand may you be blessed abundantly today, tomorrow and the days to come! \nMay you have a fantastic birthday and many more to come... \nHAPPY BIRTHDAY!!!!")
    messages.append("There is no \"I\" in team but there is in BIRTHDAY, so make it all about \"U\".")
    messages.append("They say you lose your memory as you grow older. \nI say \"forget about the past\" and live life to the fullest today. Start with ice cream. \nHappy Birthday.")
    messages.append("Hope you love your new age. \nIt loves you because it looks good on you. \nHappy Birthday.")
    messages.append("You will soon start a new phase of life! \nBut that can wait until you are older. \nEnjoy another year of being young. \nHappy Birthday.")
    messages.append("Have a wonderful happy, healthy birthday and many more to come. \nHappy Birthday !! ")
    messages.append("Wishing you a spectacularly beautiful birthday.")
    messages.append("You will never be as young again as you are today, so have fun. \nBut be careful, because you have never been this old before. \nHappy Birthday.")
    messages.append("You are only young once, but you can be immature forever. \nHappy Birthday.")
    messages.append("You are only young once - if you tell the truth about your age! \nHappy Birthday.")
    messages.append("You are only as old as you look - Here, use these glasses. \nHappy Birthday.")
    messages.append("You're the living proof of that age is just a number :) \nHappy Birthday!")
    messages.append("Wish you the best birthday ever! I hope you get lots of kisses and hugs. \nHappy Birthday!")
    messages.append("The candles on your cake won't start a fire if you don't light them, but that isn't what candles are for. \nKeep lighting up the world on your birthday.")
    messages.append("Today's birthday is one of mind over matter: \nIf you don't mind your age, it doesn't matter. \nHappy Birthday.")
    messages.append("Do you know what people in China do on their birthday? \nThey get older too. \nHappy Birthday.")
    messages.append("Let's celebrate the age you act not the age that you are. \nHappy Birthday.")
    messages.append("How old would you be if you didn't know how old you are? \nHappy Birthday.")
    messages.append("It takes a long time to become as young as you are. \nHappy Birthday.")
    messages.append("Friends may come and go, but birthdays accumulate. \nHappy Birthday.")
    messages.append("Life is a journey. Enjoy every mile. \nHappy Birthday.")
    messages.append("Roses are red, Violets are blue, Happy Birthday to You!")
    messages.append("You is kind. You is smart. You is important. It is your birthday. \nHappy Birthday")
    messages.append("Keep your friends close, but your birthday cake closer. \n Happy Birthday.")
    messages.append("You were born an original. Don't die a copy. \n Happy Birthday.")
    messages.append("Birthdays are good for you. The more you have, the longer you live. \nHappy Birthday.")
    messages.append("All the world is birthday cake, so take a piece, but not too much. \nHappy Birthday")
    
    for message in messages:
        logging.info('inserting message : %s' % (message))
        msg = Messages()
        msg.messageId = random()
        msg.message = message
        msg.put()

app = webapp2.WSGIApplication([('/', ReminderHandler),
                               ('/message', MessageHandler),
                               ('/config', ConfigurationHandler),
                               ('/schedule', SchedulerHandler)],
                              debug=True)