import logging
import webapp2
import jinja2
import cgi
import datetime
from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext import ndb
from datetime import timedelta

# Template for the main page
MAIN_PAGE_HTML = """\
<html>
  <body>
    <h1>Welcome to the Vote Simple landing page</h1>
    <a href="/sendmail">Click here to send email</a>
  </body>
</html>
"""

# Displays the main page
class MainPage(webapp2.RequestHandler):

    def get(self):
        self.response.write(MAIN_PAGE_HTML)

#incorporate some kind of hidden field to pass the poll information
#the "you are voting on" section is ugly. Need a way to clean it?
REROUTING_HTML = """\
<html>
  <body>
    <h1>Please select your vote below:</h1>
    <form action="www.easyvoter-stanford.appspot.com/submitvote" method="post">
    	<div>
	    	<input type="hidden" name="poll" value="%s">
	    	<input type="hidden" name="email" value="%s">
        <input type="hidden" name="pollKey" value="%i">
	    	<input type="radio" name="vote" value="1">Strongly Disagree<br>
	    	<input type="radio" name="vote" value="2">Disagree<br>
	    	<input type="radio" name="vote" value="3">Neutral<br>
	    	<input type="radio" name="vote" value="4">Agree<br>
	    	<input type="radio" name="vote" value="5">Strongly Agree<br>
        If you'd like to specify a proxy, enter their email here: <input type="text" name="proxyEmail"><br>
    	</div>
    	<div>
    		<input type="submit" value="Submit">
    	</div>
    </form>
  </body>
</html>
"""
#proxies can't specify other proxies
REROUTING_PROXY_HTML = """\
<html>
  <body>
    <h1>You have been selected to be a proxy for %s</h1>
    <h1>Please select your vote below:</h1>
    <form action="www.easyvoter-stanford.appspot.com/submitvote" method="post">
      <div>
        <input type="hidden" name="poll" value="%s">
        <input type="hidden" name="email" value="%s">
        <input type="hidden" name="pollKey" value="%i">
        <input type="radio" name="vote" value="1">Strongly Disagree<br>
        <input type="radio" name="vote" value="2">Disagree<br>
        <input type="radio" name="vote" value="3">Neutral<br>
        <input type="radio" name="vote" value="4">Agree<br>
        <input type="radio" name="vote" value="5">Strongly Agree<br>
      </div>
      <div>
        <input type="submit" value="Submit">
      </div>
    </form>
  </body>
</html>
"""

CONFIRMATION_HTML = """\
<html>
  <body> 
    <h1>Your poll has been created:</h1>
    <p>Subject: %s</p>
    <p>Recipients: %s</p>
    <form action="www.easyvoter-stanford.appspot.com/viewpollresults" method="post">
      <div>
        <input type="hidden" name="pollKey" value="%i">
      </div>
      <div>
        <input type="submit" value="See results">
      </div>
    </form>
  </body>
</html>
"""

RESULTS_TABLE = """\
<table>
  <tr>
    <td>Vote</td>
    <td>Count</td>
  </tr>
  <tr>
    <td>Strongly Disagree</td>
    <td>%i</td>
  </tr>
  <tr>
    <td>Disagree</td>
    <td>%i</td>
  </tr>
  <tr>
    <td>Neutral</td>
    <td>%i</td>
  </tr>
  <tr>
    <td>Agree</td>
    <td>%i</td>
  </tr>
  <tr>
    <td>Strongly Agree</td>
    <td>%i</td>
  </tr>
</table>
"""

#Models for data storage
class Vote(ndb.Model):
  email = ndb.StringProperty()
  #pollId is the Key of the Poll object
  pollID = ndb.StringProperty()
  value = ndb.StringProperty()
  date = ndb.DateTimeProperty(auto_now_add = True)
  proxy = ndb.StringProperty(default="")
  proxyVote = ndb.BooleanProperty(default=False)

class Poll(ndb.Model):
	#owner is person who sent initial email to create poll
  owner = ndb.StringProperty()
	#pollID is the subject of the initial email sent to create poll
  pollID = ndb.StringProperty()
  votes = ndb.StructuredProperty(Vote, repeated=True)
  date = ndb.DateTimeProperty(auto_now_add = True)
  #deadline = ndb.DateTimeProperty(auto_now_add = True)

# Processes emails that are sent
# Question - Ideally, I'd like this message just to "reply all" so the user doesn't get 2 separate emails - how do I do this?
# Additionally, I don't know how to import the mail_message content into the new email
class ProcessIncomingMailHandler(InboundMailHandler):
    def receive(self, mail_message):
        #every time a request comes in, you want it to be a new poll with no votes
        currentPoll = Poll(owner = mail_message.sender, pollID = mail_message.subject, votes = [])
        #set the poll's deadline to be 1 day
        #minute = timedelta(minutes=1)
        #currentPoll.deadline = currentPoll.date + minute
        currentPollKeyID = currentPoll.put().id()
        #send email to poll recipients
        #this doesn't work for people who don't show html in their emails. Can implement functionality later
        logging.debug(mail_message.to)
        recipients = mail_message.to
        recipients = recipients.split(', ')
        for recipient in recipients:
          logging.debug(recipient)
          mail.send_mail(sender="Vote Simple <support@easyvoter-stanford.appspotmail.com>",
                    to=recipient,
                    reply_to=mail_message.sender,
                    subject="RE: " + mail_message.subject,
                    body="If the form does not display below, please visit www.easyvoter-stanford.appspot.com/submitvote to vote!",
                    html=REROUTING_HTML %(mail_message.subject, recipient, currentPollKeyID))
        #send a confirmation email to poll creator
        mail.send_mail(sender="Vote Simple <support@easyvoter-stanford.appspotmail.com>",
                  to=mail_message.sender,
                  subject="RE: " + mail_message.subject,
                  body="If the form does not display below, please visit www.easyvoter-stanford.appspot.com/submitvote to vote!",
                  html=CONFIRMATION_HTML %(mail_message.body, mail_message.to, currentPollKeyID))

#Processes votes that are sent
class ProcessVoteHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(REROUTING_HTML)

    def post(self):
        #get parameters from the form

        #if there is a proxy email
        if (self.request.get('proxyEmail') != ""):
          #notify the proxy person
          mail.send_mail(sender="Vote Simple <support@easyvoter-stanford.appspotmail.com>",
                    to=self.request.get('proxyEmail'),
                    reply_to=self.request.get('proxyEmail'),
                    subject="RE: " + self.request.get('poll'),
                    body="If the form does not display below, please visit www.easyvoter-stanford.appspot.com/submitvote to vote!",
                    html=REROUTING_PROXY_HTML %(self.request.get('email'), self.request.get('poll'), self.request.get('email'), int(self.request.get('pollKey'))))
          self.response.write('<html><body>%s is now your proxy for this poll. Thanks!</body></html>' %(self.request.get('proxyEmail')))
        else:
          #this is always making it a proxy
          currentVote = Vote(email=self.request.get('email'), pollID=self.request.get('pollKey'), value=self.request.get('vote'), proxy=self.request.get('proxyEmail'), proxyVote=True)
          
          #query to find the poll
          idnumber = int(self.request.get('pollKey'))
          currentPoll = Poll.get_by_id(idnumber)

          #to keep track of whether it's a duplicate or late vote
          alreadySubmittedVote = False
          #beforeDeadline = False

          #so everyone has to vote before the deadline
          #if(vote.date < currentPoll.deadline):
          #  beforeDeadline = True

          #so same person can't vote twice
          for vote in currentPoll.votes:
            if(vote.email == currentVote.email):
              alreadySubmittedVote = True

          #you can only vote if you (or your proxy) hasn't voted before
          if(alreadySubmittedVote == True):
            self.response.write('<html><body>You (or your proxy) already voted!</body></html>')
          #elif(beforeDeadline == False):
          #  self.response.write('<html><body>You missed the voting deadline!</body></html>')
          else:
            self.response.write('<html><body>Your vote:<pre>')
            self.response.write(cgi.escape(self.request.get('vote')))
            self.response.write('</pre></body></html>')

            currentPoll.votes.append(currentVote) 
            currentPoll.put()

class ViewPollResultsHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write(CONFIRMATION_HTML)

  def post(self):
    currentPollID = int(self.request.get('pollKey'))
    currentPoll = Poll.get_by_id(currentPollID)

    results = [0,0,0,0,0]

    for vote in currentPoll.votes:
      index = int(vote.value)-1
      results[index] += 1

    self.response.write('<html>')
    self.response.write("""
      <head>
    <!--Load the AJAX API-->
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">

      // Load the Visualization API and the piechart package.
      google.load('visualization', '1.0', {'packages':['corechart']});

      // Set a callback to run when the Google Visualization API is loaded.
      google.setOnLoadCallback(drawChart);

      // Callback that creates and populates a data table,
      // instantiates the pie chart, passes in the data and
      // draws it.
      function drawChart() {

        // Create the data table.
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Response');
        data.addColumn('number', 'Number Respondents');
        data.addRows([
          ['Strongly Disagree', %i],
          ['Disagree', %i],
          ['Neutral', %i],
          ['Agree', %i],
          ['Strongly Agree', %i]
        ]);

        // Set chart options
        var options = {'title':'Poll Responses',
                       'width':400,
                       'height':300};

        // Instantiate and draw our chart, passing in some options.
        var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
        chart.draw(data, options);
      }
    </script>
  </head>
  """ %(results[0], results[1], results[2], results[3], results[4]))
    self.response.write('<div id="chart_div"></div>')
    self.response.write(RESULTS_TABLE %(results[0], results[1], results[2], results[3], results[4]))
    self.response.write('<p>The average vote: %i' %(sum(results)/float(len(results))))
    self.response.write('</body></html>')

incomingmailapp = webapp2.WSGIApplication([ProcessIncomingMailHandler.mapping()], debug=True)
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/submitvote', ProcessVoteHandler),
    ('/viewpollresults', ViewPollResultsHandler),
], debug=True)